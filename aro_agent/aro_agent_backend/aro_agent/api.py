from __future__ import annotations
import os, json, hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from .agents.coordinator import CoordinatorAgent
from .utils.compress import make_zip

from dotenv import load_dotenv
ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=ROOT_DIR / ".env", override=False)

# --- config from env ---
OUT_ROOT = Path(os.environ.get("ARO_OUT_ROOT", "out")).resolve()
OUT_ROOT.mkdir(parents=True, exist_ok=True)

MAIL_FROM = (os.environ.get("ARO_MAIL_FROM", "") or "").strip()

# Fallback order: ARO_CONTACT_EMAIL → ARO_MAIL_FROM → default string
CROSSREF_CONTACT = (
    os.environ.get("ARO_CONTACT_EMAIL", "").strip()
    or MAIL_FROM
    or "contact@example.com"
)

GMAIL_CREDS = os.environ.get(
    "ARO_GMAIL_CREDS",
    str((Path(__file__).resolve().parent.parent / "google_client_credentials.json")),
)
GMAIL_TOKEN = os.environ.get(
    "ARO_GMAIL_TOKEN",
    str((Path(__file__).resolve().parent.parent / "google_token.json")),
)

app = FastAPI(title="ARO-Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- helpers & models ----------

# --- Next-run helpers --------------------------------------------------------
from datetime import datetime, timedelta, timezone

def _iso_utc(dt: datetime) -> str:
    """Return an ISO8601 with Z."""
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def _parse_hhmm(s: str | None, default_h: int, default_m: int) -> tuple[int, int]:
    """Parse 'HH:MM' into (h, m)."""
    if not s:
        return default_h, default_m
    try:
        h, m = s.split(":")
        return max(0, min(23, int(h))), max(0, min(59, int(m)))
    except Exception:
        return default_h, default_m

def _compute_next_from_config(cfg: dict) -> str | None:
    """
    Compute the next run time in UTC based on a very small config surface:
      {
        "enabled": true,
        "frequency": "hourly" | "daily" | "weekly",
        "time": "HH:MM",        # optional, default 09:00
        "start": "<iso8601>"    # optional baseline; set when enabling
      }
    If disabled or insufficient data, returns None.
    """
    if not cfg or not cfg.get("enabled"):
        return None

    freq = (cfg.get("frequency") or "weekly").lower()
    hh, mm = _parse_hhmm(cfg.get("time"), 9, 0)

    now = datetime.now(timezone.utc)

    # Baseline: if user gave a start anchor, align to its wall-clock time
    baseline = None
    s = cfg.get("start")
    if s:
        try:
            # FastAPI / pydantic already used elsewhere; keep it simple here
            baseline = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            baseline = None

    if freq == "hourly":
        nxt = (now.replace(minute=mm, second=0, microsecond=0))
        if nxt <= now:
            nxt += timedelta(hours=1)
        return _iso_utc(nxt)

    # Daily & Weekly anchor at hh:mm UTC
    today_anchor = now.replace(hour=hh, minute=mm, second=0, microsecond=0)

    if freq == "daily":
        nxt = today_anchor if today_anchor > now else today_anchor + timedelta(days=1)
        return _iso_utc(nxt)

    if freq == "weekly":
        # If we have a baseline, keep the same weekday as the baseline.
        weekday_target = (baseline.weekday() if baseline else now.weekday())  # 0=Mon
        # Anchor the "this week" day at hh:mm
        # Compute days ahead to next target weekday strictly after now
        days_ahead = (weekday_target - now.weekday()) % 7
        anchor = today_anchor + timedelta(days=days_ahead)
        if anchor <= now:
            anchor += timedelta(days=7)
        return _iso_utc(anchor)

    # Unknown frequency -> no prediction
    return None


def _resolve_artifacts(art: dict[str, str] | None) -> dict[str, str]:
    """Resolve relative paths against OUT_ROOT; verify existence."""
    out: dict[str, str] = {}
    art = art or {}
    for k, p in art.items():
        if not p:
            continue
        pp = Path(p)
        if not pp.is_absolute():
            pp = (OUT_ROOT / p).resolve()
        out[k] = str(pp)
    return out

def _job_key_from_meta(meta: dict[str, Any]) -> dict[str, Any]:
    """Extracts the job key from the metadata."""
    query = (meta.get("query") or "").strip()
    from_year = meta.get("from_year")
    to_year = meta.get("to_year")
    enabled = meta.get("sources_enabled") or {}
    sources = sorted([k for k, v in enabled.items() if v])
    return {"query": query, "from_year": from_year, "to_year": to_year, "sources": sources}

def _job_id_from_key(key: dict[str, Any]) -> str:
    """Generates a job ID from the job key."""
    j = json.dumps(key, sort_keys=True).encode("utf-8")
    return hashlib.sha1(j).hexdigest()[:12]

def _job_dir(job_id: str) -> Path:
    """Returns the job directory path."""
    return OUT_ROOT / "jobs" / job_id

def _job_schedule_path(job_id: str) -> Path:
    """Returns the path to the job schedule file."""
    return _job_dir(job_id) / "SCHEDULE.json"

def _get_job_schedule(job_id: str) -> dict[str, Any]:
    """Retrieves the job schedule configuration."""
    p = _job_schedule_path(job_id)
    cfg: dict[str, Any] = {"enabled": False, "frequency": "weekly"}
    if p.exists():
        try:
            cfg.update(json.loads(p.read_text(encoding="utf-8")) or {})
        except Exception:
            pass
    # compute "next" every time we read
    cfg["next"] = _compute_next_from_config(cfg)
    return cfg


def _safe_under_out(p: Path) -> bool:
    """Checks if a path is safely under the OUT_ROOT."""
    try:
        return str(p.resolve()).startswith(str(OUT_ROOT.resolve()))
    except Exception:
        return False

class RunRequest(BaseModel):
    """Model for the run request body."""
    query: str = Field(..., description="Search query, e.g. 'machine learning fraud'")
    per_source_limit: int = Field(50, ge=1, le=1000)
    from_year: Optional[int] = None
    to_year: Optional[int] = None
    contact_email: Optional[str] = None
    timeout: float = Field(15.0, ge=1.0, le=120.0)
    enable_sources: Optional[Dict[str, bool]] = None  # {"arxiv":true,"crossref":true,"doaj":true}

class RunListItem(BaseModel):
    """Model for a run list item."""
    id: str
    job_id: str
    key: dict
    has_schedule: bool
    timestamp: Optional[str] = None
    query: Optional[str] = None
    counts: dict = Field(default_factory=dict)
    new_items: int = 0

class Job(BaseModel):
    """Model for a job (group of runs)."""
    job_id: str
    key: dict
    query: Optional[str]
    schedule: dict
    runs: List[RunListItem]

def _list_runs() -> List[RunListItem]:
    """Lists all runs."""
    runs: List[RunListItem] = []
    if OUT_ROOT.exists():
        for d in sorted(OUT_ROOT.glob("run_*"), key=lambda p: p.name, reverse=True):
            if not d.is_dir(): 
                continue

            # read meta from run.json
            meta: dict[str, Any] = {}
            query = None
            counts = {}
            timestamp = None
            rj = d / "run.json"
            if rj.exists():
                try:
                    meta = json.loads(rj.read_text(encoding="utf-8")) or {}
                    query = meta.get("query")
                    counts = meta.get("counts") or {}
                    timestamp = meta.get("timestamp")
                except Exception:
                    meta = {}

            # diff.csv new item count
            new_items = 0
            diff = d / "diff.csv"
            if diff.exists():
                try:
                    with diff.open("r", encoding="utf-8") as f:
                        new_items = max(0, sum(1 for _ in f) - 1)
                except Exception:
                    new_items = 0

            # compute job id
            key = _job_key_from_meta(meta) if meta else {"query": query, "from_year": None, "to_year": None, "sources": []}
            job_id = _job_id_from_key(key)
            has_schedule = _job_schedule_path(job_id).exists()

            runs.append(RunListItem(
                id=d.name, job_id=job_id, key=key, has_schedule=has_schedule,
                timestamp=timestamp, query=query, counts=counts, new_items=new_items
            ))
    return runs

def _list_jobs() -> List[Job]:
    """Lists all jobs."""
    jobs: dict[str, Job] = {}
    for r in _list_runs():
        j = jobs.get(r.job_id)
        if not j:
            j = Job(job_id=r.job_id, key=r.key, query=r.query,
                    schedule=_get_job_schedule(r.job_id), runs=[])
            jobs[r.job_id] = j
        j.runs.append(r)
    # sort runs within job
    for j in jobs.values():
        j.runs.sort(key=lambda x: x.id, reverse=True)
    # sort jobs by newest run id
    ordered = sorted(jobs.values(), key=lambda j: j.runs[0].id if j.runs else "", reverse=True)
    return ordered

# ---------- routes ----------

@app.get("/", include_in_schema=False)
def root():
    """Root endpoint."""
    return {"service": "aro-agent-api", "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

# Create a run (search)
@app.post("/runs")
def create_run(req: RunRequest):
    """Creates a new run."""
    agent = CoordinatorAgent(
        contact_email=req.contact_email or CROSSREF_CONTACT,
        timeout=req.timeout,
        enable_sources=req.enable_sources,
        run_root=OUT_ROOT,
    )
    try:
        result = agent.run(
            query=req.query,
            per_source_limit=req.per_source_limit,
            from_year=req.from_year,
            to_year=req.to_year,
        )
    except Exception as e:
        raise HTTPException(500, f"Run failed: {e}")

    latest = sorted(OUT_ROOT.glob("run_*"))[-1]
    return JSONResponse({"ok": True, "run_id": latest.name, "out_dir": str(latest), "summary": result.get("summary", {})})

# List runs (home)
@app.get("/runs", response_model=List[RunListItem])
def get_runs():
    """Lists all runs."""
    return _list_runs()

# Jobs (grouped runs)
@app.get("/jobs", response_model=List[Job])
def get_jobs():
    """Lists all jobs."""
    return _list_jobs()

# View a single run
@app.get("/runs/{run_id}")
def get_run(run_id: str):
    """Retrieves a single run by ID."""
    run_dir = OUT_ROOT / run_id
    if not run_dir.exists(): raise HTTPException(404, "Run not found")

    rj = run_dir / "run.json"
    if not rj.exists(): raise HTTPException(404, "run.json missing")

    try:
        meta = json.loads(rj.read_text(encoding="utf-8"))
    except Exception:
        meta = {}

    csv_p = run_dir / "results.csv"
    json_p = run_dir / "results.json"
    sql_p = run_dir / "results.sqlite"
    bib_p = run_dir / "results.bib"

    def _rel(p: Path) -> str | None:
        return str(p.resolve().relative_to(OUT_ROOT)) if p.exists() else None

    links = {"csv": _rel(csv_p), "json": _rel(json_p), "sqlite": _rel(sql_p), "bibtex": _rel(bib_p)}
    job_id = _job_id_from_key(_job_key_from_meta(meta))  # or grab from your computed key if you have it
    sched = _get_job_schedule(job_id) if job_id else {"enabled": False, "next": None}
    rows_preview = []
    if json_p.exists():
        try:
            data = json.loads(json_p.read_text(encoding="utf-8")) or []
            rows_preview = data[:50] if isinstance(data, list) else data
        except Exception:
            rows_preview = []

    return {"meta": meta, "links": links, "preview": rows_preview,"schedule": sched}

# Stream artifact safely from OUT_ROOT
@app.get("/artifact/{subpath:path}")
def get_artifact(subpath: str):
    """Retrieves an artifact by subpath."""
    full = (OUT_ROOT / subpath).resolve()
    if not _safe_under_out(full) or not full.exists() or not full.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(str(full), filename=full.name)

# Download SCHEDULE.txt (per run)
@app.get("/runs/{run_id}/schedule.txt")
def run_schedule_text(run_id: str):
    """Downloads the schedule text file for a run."""
    run_dir = OUT_ROOT / run_id
    if not run_dir.exists(): raise HTTPException(404, "Run not found")
    path = run_dir / "SCHEDULE.txt"
    if not path.exists(): raise HTTPException(404, "SCHEDULE.txt not found")
    return FileResponse(str(path), filename="SCHEDULE.txt")

# Enable run schedule (writes SCHEDULE.txt)
@app.post("/runs/{run_id}/schedule/enable")
def enable_run_schedule(run_id: str):
    """Enables the run schedule."""
    run_dir = OUT_ROOT / run_id
    if not run_dir.exists(): raise HTTPException(404, "Run not found")

    rj = run_dir / "run.json"
    if not rj.exists(): raise HTTPException(400, "run.json missing; cannot create schedule")

    meta = json.loads(rj.read_text(encoding="utf-8"))
    q = (meta.get("query") or "").replace('"', r'\"')
    limit = int(meta.get("per_source_limit") or 200)
    enabled = meta.get("sources_enabled") or {}
    sources = ",".join([k for k, v in enabled.items() if v])

    parts = [f'python -m aro_agent.cli --query "{q}" --limit {limit}']
    if sources: parts.append(f"--sources {sources}")
    fy = meta.get("from_year"); ty = meta.get("to_year")
    if fy is not None: parts.append(f"--from-year {fy}")
    if ty is not None: parts.append(f"--to-year {ty}")
    parts.append(f'--out "{OUT_ROOT.resolve()}"')
    base_cmd = " ".join(parts)

    schedule_text = (
        'REM ---- Windows Task Scheduler ----\n'
        f'schtasks /Create /SC WEEKLY /TN "ARO-Agent - {q}" /TR "{base_cmd}" /ST 09:00 /RL LIMITED\n\n'
        '### ---- cron (Linux/macOS) ----\n'
        '# Add this line to your crontab (crontab -e):\n'
        f'0 9 * * 1 cd "{OUT_ROOT.resolve()}" && {base_cmd} >> aro_agent.log 2>&1\n'
    )
    (run_dir / "SCHEDULE.txt").write_text(schedule_text, encoding="utf-8")
    return {"ok": True}

# Disable run schedule
@app.post("/runs/{run_id}/schedule/disable")
def disable_run_schedule(run_id: str):
    """Disables the run schedule."""
    run_dir = OUT_ROOT / run_id
    if not run_dir.exists(): raise HTTPException(404, "Run not found")
    sched = run_dir / "SCHEDULE.txt"
    if sched.exists(): sched.unlink()
    return {"ok": True}

# Enable job schedule (JSON flag)
class JobEnableBody(BaseModel):
    """Model for enabling a job schedule."""
    frequency: str | None = None      # "hourly" | "daily" | "weekly"
    time: str | None = None           # "HH:MM" (UTC)
    start: str | None = None          # ISO8601; if not given, now()

@app.post("/jobs/{job_id}/schedule/enable")
def enable_job_schedule(job_id: str, body: JobEnableBody = Body(default=JobEnableBody())):
    """Enables the job schedule."""
    jd = _job_dir(job_id); jd.mkdir(parents=True, exist_ok=True)
    sched = _job_schedule_path(job_id)

    now_iso = _iso_utc(datetime.now(timezone.utc))
    cfg = {
        "enabled": True,
        "frequency": (body.frequency or "weekly").lower(),
        "time": body.time or "09:00",
        "start": body.start or now_iso,
    }
    sched.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    # include computed next in the response
    cfg["next"] = _compute_next_from_config(cfg)
    return {"ok": True, "schedule": cfg}

@app.post("/jobs/{job_id}/schedule/disable")
def disable_job_schedule(job_id: str):
    """Disables the job schedule."""
    sched = _job_schedule_path(job_id)
    if sched.exists(): sched.unlink()
    return {"ok": True}

# Run a job now (repeat latest run params)
@app.post("/jobs/{job_id}/run")
def job_run_now(job_id: str):
    """Runs a job immediately."""
    jobs = {j.job_id: j for j in _list_jobs()}
    job = jobs.get(job_id)
    if not job or not job.runs:
        raise HTTPException(400, "No past run found to reconstruct parameters.")

    latest_run = job.runs[0]
    run_dir = OUT_ROOT / latest_run.id
    meta = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    query = meta.get("query") or ""
    limit = int(meta.get("per_source_limit") or 200)
    from_year = meta.get("from_year")
    to_year = meta.get("to_year")
    enable_sources = meta.get("sources_enabled") or {}

    agent = CoordinatorAgent(contact_email=CROSSREF_CONTACT, timeout=15.0, enable_sources=enable_sources, run_root=OUT_ROOT)
    artefacts = agent.run(query=query, per_source_limit=limit, from_year=from_year, to_year=to_year)
    newest = sorted(OUT_ROOT.glob("run_*"))[-1]
    return {"ok": True, "run_id": newest.name, "out_dir": str(newest), "artefacts": artefacts}

# Create a zip for a run's artifacts
class ZipRequest(BaseModel):
    """Model for creating a zip archive of artifacts."""
    artefacts: Dict[str, Optional[str]]  # {"csv": "...", "json":"...", "sqlite":"...", "bibtex":"..."}

@app.post("/zip")
def create_zip_and_download(payload: ZipRequest):
    """Creates a zip archive of the specified artifacts and returns it for download."""
    artefacts = payload.artefacts or {}
    json_path = artefacts.get("json")
    if not json_path:
        raise HTTPException(400, "Missing JSON artefact.")
    json_abs = Path(json_path)
    if not json_abs.is_absolute():
        json_abs = (OUT_ROOT / json_abs).resolve()
    run_dir = json_abs.parent
    if not _safe_under_out(run_dir):
        raise HTTPException(400, "Invalid run directory.")
    zip_path = run_dir / "aro_results.zip"
    make_zip([artefacts.get("csv"), artefacts.get("json"), artefacts.get("sqlite"), artefacts.get("bibtex")], zip_path)
    if not zip_path.exists():
        raise HTTPException(500, "Failed to create zip.")
    return FileResponse(str(zip_path), filename="aro_results.zip")

# Send results by email
class SendRequest(BaseModel):
    """Model for sending results by email."""
    query: str
    artefacts: Dict[str, Optional[str]]
    mail_to: str
    attach_zip: bool = False

# in /send endpoint (keep the lazy import & 501 guard you already added)
@app.post("/send")
def send_email_results(payload: SendRequest):
    """Sends the results by email."""
    try:
        from .utils.email_format import build_and_send_email
    except Exception:
        raise HTTPException(status_code=501, detail="Email feature not enabled (missing Google client libs).")

    if not MAIL_FROM:
        raise HTTPException(500, "Server missing ARO_MAIL_FROM.")

    artefacts = _resolve_artifacts(payload.artefacts)

    json_path = artefacts.get("json")
    if not json_path or not Path(json_path).is_file():
        raise HTTPException(
            status_code=400,
            detail="JSON artifact not found. Use links from GET /runs/{id} (e.g. 'run_YYYYMMDD_HHMMSS/results.json')."
        )

    recipients = [t.strip() for t in payload.mail_to.replace(";", ",").split(",") if t.strip()]
    if not recipients:
        raise HTTPException(400, "At least one recipient is required.")

    resp = build_and_send_email(
        query=payload.query,
        artefacts=artefacts,  # pass the resolved absolute paths
        sender=MAIL_FROM,
        recipients=recipients,
        credentials_path=GMAIL_CREDS,
        token_path=GMAIL_TOKEN,
        attach_zip=payload.attach_zip,
    )
    return {"ok": True, "gmail_message_id": resp.get("id")}
