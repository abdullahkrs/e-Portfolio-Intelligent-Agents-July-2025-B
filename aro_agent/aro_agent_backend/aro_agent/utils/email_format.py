import os, json, re
from collections import Counter
from pathlib import Path
from .compress import make_zip
from .email_gmail import send_email

def _infer_year(r: dict) -> int | None:
    # try common fields
    for k in ("year", "published_year"):
        v = r.get(k)
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
    # try date-like fields with regex
    for k in ("published", "date", "created"):
        v = r.get(k)
        if isinstance(v, str):
            m = re.search(r"\b(19|20)\d{2}\b", v)
            if m:
                try:
                    return int(m.group(0))
                except Exception:
                    pass
    return None

def _infer_source(r: dict) -> str:
    for k in ("source", "origin", "provider"):
        v = (r.get(k) or "").strip()
        if v:
            return v
    if r.get("doi"):
        return "crossref"
    if r.get("arxiv_id"):
        return "arxiv"
    if r.get("issn"):
        return "doaj"
    return "unknown"

def build_and_send_email(query: str, artefacts: dict, sender: str, recipients: list[str],
                         credentials_path: str, token_path: str, attach_zip: bool = True):
    """Build HTML email with stats and send via Gmail."""

    json_path = artefacts.get("json")
    if not json_path or not os.path.isfile(json_path):
        raise ValueError("results.json not found (artefacts.json)")

    # Load results.json
    with open(json_path, "r", encoding="utf-8") as f:
        rows = json.load(f) or []

    total = len(rows)

    years = [y for y in (_infer_year(r) for r in rows) if isinstance(y, int)]
    y_min = min(years) if years else None
    y_max = max(years) if years else None

    by_source = Counter(_infer_source(r) for r in rows if isinstance(r, dict) and r)
    venues = Counter((r.get("venue") or r.get("journal") or "").strip()
                     for r in rows if (r.get("venue") or r.get("journal")))
    top_venues = [(v, c) for v, c in venues.most_common(5) if v]

    def _fmt_files():
        files = []
        for k in ("csv", "json", "sqlite", "bibtex"):
            p = artefacts.get(k)
            if not p:
                continue
            try:
                sz = os.path.getsize(p)
                files.append(f"{os.path.basename(p)} ({sz:,} bytes)")
            except Exception:
                files.append(os.path.basename(p))
        return "<br>".join(files) if files else "None"

    # Build HTML
    parts = [
        "<h2>ARO-Agent results</h2>",
        f"<p><b>Query:</b> {query}</p>",
        f"<p><b>Total records:</b> {total} | <b>Year range:</b> "
        + (f"{y_min}–{y_max}" if y_min is not None and y_max is not None else "n/a")
        + "</p>",
        "<h3>By source</h3>",
        ("<ul>" + "".join(f"<li>{src}: {cnt}</li>" for src, cnt in by_source.most_common()) + "</ul>")
            if by_source else "<p>No data</p>",
        "<h3>Top venues</h3>",
        ("<ul>" + "".join(f"<li>{v}: {c}</li>" for v, c in top_venues) + "</ul>") if top_venues else "<p>No data</p>",
        "<h3>Files</h3>",
        f"<p>{_fmt_files()}</p>"
    ]

    html = "\n".join(parts)

    # Optional: create a zip and attach it
    attachments = []
    if attach_zip:
        zip_path = Path(json_path).with_name("aro_results.zip")
        make_zip([artefacts.get("csv"), artefacts.get("json"), artefacts.get("sqlite"), artefacts.get("bibtex")], zip_path)
        if zip_path.exists():
            attachments.append(str(zip_path))

    # Send
    msg_meta = send_email(
        sender=sender,
        to=recipients,
        subject="ARO-Agent results",
        html_body=html,
        attachments=attachments or None,
        credentials_path=credentials_path,
        token_path=token_path,
    )
    return msg_meta
