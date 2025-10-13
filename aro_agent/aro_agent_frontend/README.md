# ARO-Agent Web (Flask)

A minimal Flask UI on top of your existing **aro-agent** package.

## Install

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
# Make sure aro-agent (the CLI scaffold you built earlier) is importable:
# If both projects share the same parent folder, from the web folder run:
# pip install -e ../aro_agent_scaffold
```

## Run

```bash
set FLASK_APP=webapp/app.py  # PowerShell: $env:FLASK_APP="webapp/app.py"
flask run --port 8000 --debug
# or: python webapp/app.py
```

Open http://localhost:8000 and run a search. Outputs (CSV/JSON/SQLite/BibTeX/static HTML) are saved under `out/`.
