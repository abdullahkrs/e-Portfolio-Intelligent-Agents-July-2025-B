# ARO‑Agent (Academic Research Online Agent)

A lightweight, API‑first, multi‑agent Python tool that searches **arXiv**, **Crossref**, and **DOAJ**, normalises identifiers (preferring DOI with arXiv ID fallback), and exports **CSV + JSON + SQLite**, with a simple static **HTML results** page for filtering.

This implementation follows the attached design proposal (BDI‑inspired, modular agents, API‑only strategy).

## 1) Quick start

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

Run a query:

```bash
python -m aro_agent.cli --query "machine learning for fraud detection" --limit 50 --email you@example.com
```

Outputs are saved under `./out/run_YYYYmmdd_HHMMSS/`:
- `results.csv`
- `results.json`
- `results.sqlite`
- `index.html` (open in your browser for a filterable view)

> **Note**: arXiv provides an Atom XML API; this repo parses it with the Python standard library. Crossref & DOAJ are JSON.

## 2) Options

- `--no-arxiv`, `--no-crossref`, `--no-doaj` to skip specific sources
- `--limit N` max items per source (default 50)
- `--email` sets the contact email used in the Crossref User‑Agent string
- `--out PATH` sets the output root (default `out/`)

## 3) Design and BDI mapping

- **CoordinatorAgent** – executes intentions: orchestrates discovery → fetch → extract → store, deduplicates by DOI / arXiv ID.
- **DiscoveryAgent** – translates the desire (free‑text query) into concrete API calls per source.
- **FetchAgent** – reactive HTTP client with retry/backoff.
- **ExtractAgent** – builds beliefs: normalised `Record` objects from source responses.
- **StorageAgent** – persists beliefs to CSV/JSON/SQLite and emits a static HTML view.

## 4) Reproducibility

- Each run is time‑stamped.
- JSON and CSV capture the full, normalised records.
- SQLite provides a local, portable store.

## 5) Next steps / extensions

- Pagination across multiple pages per source
- More filters (year range, open‑access, subject)
- Weekly automation via OS scheduler (cron/Task Scheduler)
- Unit tests for parsers & normalisers
- Export to BibTeX / RIS

---

Made with ❤️ for transparent, reproducible academic search.
