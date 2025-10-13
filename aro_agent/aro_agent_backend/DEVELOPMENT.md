# ARO-Agent — Development Notes

## Mapping Proposal → Code
- **BDI**: `CoordinatorAgent._bdi_log`, `bdi_trace.json`, `run.json`
- **Discovery**: `agents/discovery.py` (build tasks; adds Crossref year filters; optional paginate)
- **Fetch**: `agents/fetch.py` (retry/backoff; polite UA; optional pagination; concurrency over page lists)
- **Extract**: `agents/extract.py` (normalize DOI/arXiv; parse per-source payloads)
- **Storage**: `agents/storage.py` (CSV/JSON/SQLite/BibTeX; primary_id; PRAGMAs; indexes; HTML template copy)
- **Diffing**: `Coordinator._write_diff_csv` + `diff.csv`
- **Scheduling**: `--emit-schedule` → `SCHEDULE.txt`
- **Web UI**: templates `index.html`, `assets/app.js`/`style.css` (filters + “new since last run”)

## Failure Runbook
- HTTP 429/5xx: automatic backoff; rerun if repeated
- Empty payloads: check network and API availability; try fewer sources
- Duplicates: dedupe by `primary_id` (DOI → arxiv:{id}); verify Extract normalization
- Year filters: Crossref filtered at source; others filtered post-extract
