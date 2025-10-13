# webapp/app.py
from __future__ import annotations
import os, json, threading, time
from pathlib import Path
from typing import Any, Dict, List, Optional
from flask import (
    Flask, render_template, request, redirect, url_for, flash
)
import requests

APP = Flask(__name__)
APP.secret_key = os.environ.get("ARO_SECRET_KEY", "dev-secret")
API_BASE = os.environ.get("ARO_API_BASE", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = (10, 60)  # (connect, read)

# ---------------------- API helpers ----------------------
def _full(path: str) -> str:
    """Return absolute API URL for a given path using `API_BASE`."""
    return f"{API_BASE}{path}"

def api_get(path: str, **kwargs):
    """HTTP GET wrapper against the backend API; returns JSON when available.

    Raises RuntimeError on non-2xx responses.
    """
    r = requests.get(_full(path), timeout=TIMEOUT, **kwargs)
    if not r.ok:
        raise RuntimeError(f"GET {path} -> {r.status_code}: {r.text}")
    if "application/json" in r.headers.get("content-type", ""):
        return r.json()
    return r

def api_post(path: str, json_body: dict | None = None, **kwargs):
    """HTTP POST wrapper against the backend API; returns JSON when available.

    Raises RuntimeError on non-2xx responses.
    """
    r = requests.post(_full(path), json=json_body or {}, timeout=TIMEOUT, **kwargs)
    if not r.ok:
        raise RuntimeError(f"POST {path} -> {r.status_code}: {r.text}")
    if "application/json" in r.headers.get("content-type", ""):
        return r.json()
    return r

def api_exists(path: str) -> bool:
    """Return True if GET to the given API path succeeds (2xx).

    Uses streaming GET to avoid loading large payloads.
    """
    # Safer to GET; stream to avoid loading file
    try:
        r = requests.get(_full(path), timeout=TIMEOUT, stream=True)
        return r.ok
    except Exception:
        return False

# ---------------------- Normalizers ----------------------
def normalize_run_item(r: Dict[str, Any]) -> Dict[str, Any]:
    """
    /runs returns:
      { id, job_id, key, has_schedule, timestamp, query, counts, new_items }
    UI needs:
      - date     ← timestamp
      - count    ← sum(counts.values())
      - scheduled← per-run schedule.txt (NOT job schedule)
    """
    rid = r.get("id")
    counts = r.get("counts") or {}
    try:
        total = sum(v for v in counts.values() if isinstance(v, (int, float)))
    except Exception:
        total = None

    # Per-run schedule (SCHEDULE.txt) — used by our ON/OFF on results & index rows
    run_sched = api_exists(f"/runs/{rid}/schedule.txt") if rid else False

    return {
        "id": rid,
        "run_id": rid,
        "job_id": r.get("job_id"),
        "query": r.get("query"),
        "date": r.get("timestamp"),
        "count": total,
        "scheduled": run_sched,         # per-run flag
        "job_has_schedule": bool(r.get("has_schedule")),  # job-level schedule JSON (FYI)
        "new_items": r.get("new_items", 0),
    }

# ---------------------- Email-after-run helpers ----------------------
def poll_run_artifacts(run_id: str, *, timeout: int = 900, interval: float = 5.0) -> dict:
    """Poll `/runs/{id}` until any artifact link appears; return `links` or `{}`."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data = api_get(f"/runs/{run_id}")  # {'meta','links','preview','schedule'}
            links = (data or {}).get("links") or {}
            if any(links.get(k) for k in ("csv", "json", "sqlite", "bibtex")):
                return links
        except Exception:
            pass
        time.sleep(interval)
    return {}

def request_send_email(query: str, mail_to: str, links: dict):
    """Request the backend to send results email with provided artefact links."""
    payload = {
        "query": query or "",
        "artefacts": {k: links.get(k) for k in ("csv", "json", "sqlite", "bibtex")},
        "mail_to": mail_to,
        "attach_zip": False,  # no ZIP per your UI
    }
    api_post("/send", json_body=payload)

def auto_email_after_run(run_id: str, query: str, mail_to: str):
    """Background worker: waits for artefacts then triggers email send."""
    try:
        links = poll_run_artifacts(run_id)
        if links:
            request_send_email(query=query, mail_to=mail_to, links=links)
    except Exception:
        # swallow errors; you can add logging here
        pass

# ---------------------- Routes ----------------------
@APP.route("/", methods=["GET", "POST"])
def index():
    """Index page: create a new run (POST) or list runs (GET)."""
    # Create run
    if request.method == "POST":
        payload = {
            "query": (request.form.get("query") or "").strip(),
            "per_source_limit": int(request.form.get("limit") or 50),
            "from_year": int(request.form["from_year"]) if request.form.get("from_year") else None,
            "to_year": int(request.form["to_year"]) if request.form.get("to_year") else None,
            "contact_email": request.form.get("contact_email") or None,
            "timeout": float(request.form.get("timeout") or 15.0),
            # Optional sources: comma-separated list "arxiv,crossref,doaj"
            "enable_sources": {
                k.strip(): True for k in (request.form.get("sources") or "").split(",") if k.strip()
            } or None,
        }
        try:
            resp = api_post("/runs", json_body=payload)
            rid = resp.get("run_id")

            # If user provided an email, auto-send after artifacts are ready
            contact_email = payload.get("contact_email")
            if contact_email and rid:
                threading.Thread(
                    target=auto_email_after_run,
                    args=(rid, payload.get("query",""), contact_email),
                    daemon=True,
                ).start()

            flash("Run created.", "success")
            return redirect(url_for("run_detail", run_id=rid))
        except Exception as e:
            flash(str(e), "error")
            return redirect(url_for("index"))

    # List runs
    runs_raw: List[Dict[str, Any]]
    try:
        runs_raw = api_get("/runs") or []
    except Exception as e:
        runs_raw = []
        flash(f"Could not load runs: {e}", "error")

    # Normalize for the templates
    runs = [normalize_run_item(r) for r in runs_raw if isinstance(r, dict)]

    return render_template("index.html", runs=runs, api_base=API_BASE)

@APP.route("/runs/<run_id>")
def run_detail(run_id: str):
    """Run details page: shows preview, artefacts, and schedule status."""
    # Single run view
    try:
        data = api_get(f"/runs/{run_id}")  # { meta, links, preview, schedule }
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for("index"))

    links = data.get("links") or {}
    raw_artifacts = {k: (links.get(k) or None) for k in ("csv", "json", "sqlite", "bibtex")}
    artifact_urls = {k: (f"{API_BASE}/artifact/{v}" if v else None) for k, v in raw_artifacts.items()}

    # Job-level schedule (enabled + next) now comes from the API response
    sched = data.get("schedule") or {}
    job_schedule_enabled = bool(sched.get("enabled"))
    job_schedule_next = sched.get("next")

    # Per-run simple toggle (SCHEDULE.txt) still supported & used by our button
    run_scheduled = api_exists(f"/runs/{run_id}/schedule.txt")

    return render_template(
        "results.html",
        run_id=run_id,
        meta=data.get("meta") or {},
        preview=data.get("preview") or [],
        artifacts=artifact_urls,       # absolute URLs for download buttons
        raw_artifacts=raw_artifacts,   # relative paths sent to /send
        run_scheduled=run_scheduled,   # used by ON/OFF button
        job_schedule_enabled=job_schedule_enabled,  # for display if you want
        job_schedule_next=job_schedule_next,        # for display if you want
        api_base=API_BASE,
    )

# ---- Run-level schedule (uses SCHEDULE.txt) ----
@APP.route("/runs/<run_id>/schedule/enable", methods=["POST"])
def run_schedule_enable(run_id: str):
    """Enable per-run schedule (SCHEDULE.txt) for this run."""
    try:
        api_post(f"/runs/{run_id}/schedule/enable")
        flash("Schedule enabled for this run.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("run_detail", run_id=run_id))

@APP.route("/runs/<run_id>/schedule/disable", methods=["POST"])
def run_schedule_disable(run_id: str):
    """Disable per-run schedule (SCHEDULE.txt) for this run."""
    try:
        api_post(f"/runs/{run_id}/schedule/disable")
        flash("Schedule disabled for this run.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("run_detail", run_id=run_id))

# ---- Jobs/Schedules (job-level grouping & JSON flag) ----
@APP.route("/jobs")
def jobs():
    """Jobs page: list jobs with schedule status and last run."""
    try:
        raw_jobs = api_get("/jobs") or []
    except Exception as e:
        raw_jobs = []
        flash(f"Could not load jobs: {e}", "error")

    jobs = []
    for j in raw_jobs:
        if not isinstance(j, dict):
            continue

        # API returns {"job_id","key","query","schedule":{enabled,next,...},"runs":[...]}
        sched = j.get("schedule") or {}
        enabled = bool(sched.get("enabled"))
        next_run = sched.get("next")

        jobs.append({
            "id": j.get("job_id") or j.get("id"),
            "query": j.get("query"),
            "title": j.get("title") or j.get("name") or j.get("query"),
            "enabled": enabled,
            "next_run": next_run or "—",
            "last_run_id": (j.get("runs")[0]["id"] if j.get("runs") else None),
        })

    return render_template("schedule.html", jobs=jobs, api_base=API_BASE)

@APP.route("/jobs/<job_id>/schedule/enable", methods=["POST"])
def job_schedule_enable(job_id: str):
    """Enable job-level scheduler using API defaults."""
    try:
        api_post(f"/jobs/{job_id}/schedule/enable")  # uses API defaults (weekly @ 09:00Z)
        flash("Job schedule enabled.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("jobs"))

@APP.route("/jobs/<job_id>/schedule/disable", methods=["POST"])
def job_schedule_disable(job_id: str):
    """Disable job-level scheduler."""
    try:
        api_post(f"/jobs/{job_id}/schedule/disable")
        flash("Job schedule disabled.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("jobs"))

@APP.route("/jobs/<job_id>/run", methods=["POST"])
def job_run_now(job_id: str):
    """Trigger an immediate run for the given job and redirect to it."""
    try:
        resp = api_post(f"/jobs/{job_id}/run")
        rid = resp.get("run_id")
        flash("Job started; new run created.", "success")
        return redirect(url_for("run_detail", run_id=rid))
    except Exception as e:
        flash(str(e), "error")
        return redirect(url_for("jobs"))

# ---- Email proxy to API ----
@APP.route("/send", methods=["POST"])
def send_results():
    """Proxy form submission to backend `/send` email endpoint."""
    query = request.form.get("query", "").strip()
    mail_to = request.form.get("mail_to", "").strip()
    artefacts = {
        "csv": request.form.get("csv") or None,
        "json": request.form.get("json") or None,
        "sqlite": request.form.get("sqlite") or None,
        "bibtex": request.form.get("bibtex") or None,
    }
    try:
        resp = api_post("/send", json_body={
            "query": query,
            "artefacts": artefacts,
            "mail_to": mail_to,
            "attach_zip": False  # no ZIP in UI
        })
        msgid = resp.get("gmail_message_id")
        flash("Email sent." if msgid else "Email requested.", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(request.referrer or url_for("index"))

# (ZIP endpoint kept if you still expose it via the API; button hidden in UI)
@APP.route("/zip", methods=["POST"])
def zip_results():
    """Download a ZIP of selected artefacts via backend proxy."""
    artefacts = {
        "csv": request.form.get("csv") or None,
        "json": request.form.get("json") or None,
        "sqlite": request.form.get("sqlite") or None,
        "bibtex": request.form.get("bibtex") or None,
    }
    try:
        r = requests.post(_full("/zip"), json={"artefacts": artefacts}, timeout=TIMEOUT, stream=True)
        if r.status_code != 200:
            raise RuntimeError(f"Zip failed: {r.status_code} {r.text}")
        headers = {"Content-Disposition": "attachment; filename=aro_results.zip"}
        return APP.response_class(
            r.iter_content(chunk_size=8192),
            headers=headers,
            mimetype="application/zip",
            direct_passthrough=True,
        )
    except Exception as e:
        flash(str(e), "error")
        return redirect(request.referrer or url_for("index"))

# ---- Jinja filters ----
@APP.template_filter("join_authors")
def join_authors(auth):
    """Join list of author names with '; ' for display in templates."""
    if isinstance(auth, list):
        return "; ".join(a for a in auth if a)
    return auth or ""

# ---- Entrypoint ----
if __name__ == "__main__":
    APP.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
