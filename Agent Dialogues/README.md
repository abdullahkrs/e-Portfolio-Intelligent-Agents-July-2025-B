
# Agent Dialogue (KQML + KIF): Alice ↔ Bob Warehouse Demo

A **complete, working** example of two software agents communicating via **KQML** (message envelopes) with **KIF** (logical content) over HTTP.

- **Alice** — procurement agent (client).
- **Bob** — warehouse stock agent (FastAPI server).

This README includes: **overview, features, architecture, setup (Windows/macOS/Linux), Quick Start, usage, full endpoint docs, ontology details, sample transcripts, troubleshooting, roadmap, and GitHub push instructions.**

---

## Table of Contents
1. Features
2. Architecture
3. Requirements
4. Quick Start
5. Usage
   - Run Bob (server)
   - Run Alice (client)
   - Expected Output
6. Endpoints (Bob)
7. Protocol Details
   - KQML Envelope
   - Supported Performatives
8. Warehouse Ontology (KIF)
9. Manual HTTP Tests (curl)
10. Project Structure
11. Configuration & Extending
12. Troubleshooting
13. Roadmap
14. Contributing
15. License
16. Push to GitHub

---

## Features
- **KQML** messages over **HTTP** with **KIF** content.
- `ask-one` (check stock), `ask-one` (HDMI slots), `achieve` (reserve), and `ask-all` (list all 50" models).
- **FastAPI** server for Bob (`POST /kqml`).
- **Simple in-memory KB** with two 50" TV models.
- **Client transcript + clean summary** parsing.
- Easy to extend with more SKUs, performatives, or a real database.

---

## Architecture
```
Alice (client)  --HTTP-->  Bob (FastAPI server)
   KQML:ask-one            parses KQML envelope
   KIF content             pattern-matches KIF atoms
                           replies with KQML:tell carrying KIF facts
```

- **Transport:** HTTP (text/plain body carrying a KQML S-expression).
- **Envelope Language:** KQML performatives (e.g., `ask-one`, `tell`, `achieve`, `deny`, `sorry`).
- **Content Language:** KIF atoms representing a tiny warehouse ontology.

---

## Requirements
- **Python 3.10+** (tested on Windows with Python 3.11)
- `pip install -r requirements.txt`
- Works on Windows, macOS, Linux

> Tip (Windows): use a **virtual environment** so the interpreter that installs packages is the same one that runs `uvicorn`.

---

## Quick Start

### 1) Create & activate a virtual environment
**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux (bash)**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies
```bash
pip install -r requirements.txt
```

### 3) Run Bob (server)
```bash
python -m uvicorn bob_server:app --reload --port 8000
```
Bob listens at **http://127.0.0.1:8000**.

### 4) Run Alice (client) in another terminal (same venv)
```bash
python alice_client.py
```

---

## Usage

### Run Bob (server)
```bash
python -m uvicorn bob_server:app --reload --port 8000
```

### Run Alice (client)
```bash
python alice_client.py
```

### Expected Output
A transcript like:
```
(ask-one ...)           → (tell ... available-quantity ...)
(ask-one (hdmi-slots))  → (tell (hdmi-slots ...))
(achieve (reserve ...)) → (tell (reserved ...) (available-quantity ...))
(ask-all ...)           → (tell (and (and ...) (and ...)))
```

And a summary like:
```
Summary:
- First 50" SKU: SKU-50TV-ABC, initial qty: 42
- HDMI reply: (hdmi-slots SKU-50TV-ABC 3)
- Reserved 5 units → new available quantity for SKU-50TV-ABC: 37
- ask-all inventory:
  • TVM-50-ULTRA (SKU-50TV-ABC) → qty 37
  • TVM-50-VISTA (SKU-50TV-XYZ) → qty 17
```

---

## Endpoints (Bob)

### `POST /kqml`
- **Content-Type:** `text/plain`
- **Body:** A KQML S-expression. The `:content` field carries **KIF**.

#### 1) `ask-one` — Stock for 50" TVs
**Request**
```lisp
(ask-one
  :sender Alice
  :receiver Bob
  :language KIF
  :ontology warehouse-ontology-v1
  :reply-with m1
  :conversation-id procure-2025-09-07-001
  :content (and
      (instance ?m TelevisionModel)
      (size-inch ?m 50)
      (model-sku ?m ?sku)
      (available-quantity ?sku ?qty)))
```

**Reply (example)**
```lisp
(tell
  :sender Bob
  :receiver Alice
  :language KIF
  :ontology warehouse-ontology-v1
  :in-reply-to m1
  :reply-with m2
  :conversation-id procure-2025-09-07-001
  :content (and
      (instance TVM-50-ULTRA TelevisionModel)
      (size-inch TVM-50-ULTRA 50)
      (model-sku TVM-50-ULTRA SKU-50TV-ABC)
      (available-quantity SKU-50TV-ABC 42)))
```

#### 2) `ask-one` — HDMI ports for a SKU
**Request**
```lisp
(ask-one
  :sender Alice
  :receiver Bob
  :language KIF
  :ontology warehouse-ontology-v1
  :in-reply-to m2
  :reply-with m3
  :conversation-id procure-2025-09-07-001
  :content (hdmi-slots SKU-50TV-ABC ?n))
```

**Reply**
```lisp
(tell
  :sender Bob
  :receiver Alice
  :language KIF
  :ontology warehouse-ontology-v1
  :in-reply-to m3
  :conversation-id procure-2025-09-07-001
  :content (hdmi-slots SKU-50TV-ABC 3))
```

#### 3) `achieve` — Reserve N units
**Request**
```lisp
(achieve
  :sender Alice
  :receiver Bob
  :language KIF
  :ontology warehouse-ontology-v1
  :reply-with mA
  :conversation-id procure-2025-09-07-001
  :content (reserve SKU-50TV-ABC 5))
```

**Reply (success)**
```lisp
(tell
  :sender Bob
  :receiver Alice
  :language KIF
  :ontology warehouse-ontology-v1
  :in-reply-to mA
  :conversation-id procure-2025-09-07-001
  :content (and
    (reserved SKU-50TV-ABC 5)
    (available-quantity SKU-50TV-ABC 37)))
```

**Reply (deny)**
```lisp
(deny
  :sender Bob
  :receiver Alice
  :in-reply-to mA
  :conversation-id procure-2025-09-07-001
  :content (insufficient-quantity SKU-50TV-ABC requested 100 available 37))
```

#### 4) `ask-all` — List all 50" models + quantities
**Request**
```lisp
(ask-all
  :sender Alice
  :receiver Bob
  :language KIF
  :ontology warehouse-ontology-v1
  :reply-with m1b
  :conversation-id procure-2025-09-07-001
  :content (and
      (instance ?m TelevisionModel)
      (size-inch ?m 50)
      (model-sku ?m ?sku)
      (available-quantity ?sku ?qty)))
```

**Reply (example)**
```lisp
(tell
  :sender Bob
  :receiver Alice
  :language KIF
  :ontology warehouse-ontology-v1
  :in-reply-to m1b
  :reply-with m2-all
  :conversation-id procure-2025-09-07-001
  :content (and
    (and
      (instance TVM-50-ULTRA TelevisionModel)
      (size-inch TVM-50-ULTRA 50)
      (model-sku TVM-50-ULTRA SKU-50TV-ABC)
      (available-quantity SKU-50TV-ABC 37))
    (and
      (instance TVM-50-VISTA TelevisionModel)
      (size-inch TVM-50-VISTA 50)
      (model-sku TVM-50-VISTA SKU-50TV-XYZ)
      (available-quantity SKU-50TV-XYZ 17))))
```

---

## Protocol Details

### KQML Envelope
Common keys used here:
- `:sender` — agent name (e.g., `Alice`).
- `:receiver` — agent name (e.g., `Bob`).
- `:language` — `KIF` (content language).
- `:ontology` — `warehouse-ontology-v1` (shared vocabulary).
- `:reply-with` — message id from sender, used for correlation.
- `:in-reply-to` — previous message id being answered.
- `:conversation-id` — group messages into one task flow.
- `:content` — **KIF** expression (query or fact).

### Supported Performatives
- `ask-one` — request a single answer.
- `ask-all` — request all matching answers.
- `tell` — provide information.
- `achieve` — request an action be performed (e.g., reserve stock).
- `deny` — refuse a requested action.
- `sorry` — “not-understood” / error fallback.

---

## Warehouse Ontology (KIF)

Predicates used:
```lisp
(define-class TelevisionModel)
(define-fun size-inch (TelevisionModel Integer))
(define-fun model-sku  (TelevisionModel Symbol))
(define-fun available-quantity (Symbol Integer))
(define-fun hdmi-slots (Symbol Integer))
```

Example facts:
```lisp
(instance TVM-50-ULTRA TelevisionModel)
(size-inch TVM-50-ULTRA 50)
(model-sku TVM-50-ULTRA SKU-50TV-ABC)
(available-quantity SKU-50TV-ABC 42)
(hdmi-slots SKU-50TV-ABC 3)
```

---

## Manual HTTP Tests (curl)

With **Bob** running:
```bash
curl -X POST http://127.0.0.1:8000/kqml -H "Content-Type: text/plain" --data-binary '(ask-one
  :sender Alice
  :receiver Bob
  :language KIF
  :ontology warehouse-ontology-v1
  :reply-with m1
  :conversation-id procure-2025-09-07-001
  :content (and
    (instance ?m TelevisionModel)
    (size-inch ?m 50)
    (model-sku ?m ?sku)
    (available-quantity ?sku ?qty)))'
```

---

## Project Structure
```
.
├─ alice_client.py       # Sends KQML; prints transcript & summary
├─ bob_server.py         # FastAPI server; processes KQML on POST /kqml
├─ warehouse.kif         # Tiny KIF/SUO-KIF-style snippet (informational)
├─ requirements.txt      # Runtime dependencies
├─ LICENSE               # MIT
└─ README.md
```

---

## Configuration & Extending
- **KB**: edit `KB` in `bob_server.py` to add SKUs, sizes, HDMI ports, and starting quantities.
- **Port**: change `--port` when running uvicorn (default example uses `8000`).
- **New capabilities**: add more KQML performatives (`ask-if`, `subscribe`, …).
- **Persistence**: swap the `KB` dict for SQLite/PostgreSQL for real inventory.

---

## Troubleshooting
- **ModuleNotFoundError (e.g., `sexpdata`)**  
  Make sure you’re in the same **virtualenv** for `pip install` **and** for running `uvicorn`/`python`.
- **Port already in use**  
  Use a different `--port` or free the port.
- **Mixed Python versions (e.g., 3.11 vs 3.13)**  
  Always run with `python -m uvicorn ...` from the activated venv.

---

## Roadmap
- `subscribe` callbacks for stock changes.
- Unification for KIF variables (replace regex).
- DB-backed stock (SQLite/Postgres) with migrations.
- Additional product attributes and queries (brand, resolution, etc.).

---

## Contributing
PRs welcome! Please keep the demo minimal and well-commented. Feel free to add tests and a CI workflow.

---

## License
MIT — see `LICENSE`.

---

## Push to GitHub

**Using Git:**
```bash
git init
git add .
git commit -m "Initial commit: KQML/KIF Alice↔Bob demo"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO>.git
git push -u origin main
```

**Using GitHub CLI:**
```bash
gh repo create <YOUR_REPO> --public --source . --remote origin --push
```
