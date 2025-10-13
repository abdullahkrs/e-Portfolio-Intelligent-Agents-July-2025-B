# 🧠 ARO Agent — Backend API (`aro_agent_backend`)

## 📘 Overview
The **ARO Agent Backend** is the core service responsible for managing automated research workflows, processing academic data, and providing REST API endpoints for frontend and external integrations.  
It forms the **intelligence layer** of the *Academic Research Online Agent (ARO Agent)* system.

This module performs:
- Research discovery  
- Data extraction and normalization  
- Result storage and export  
- Task scheduling and reporting  

It is built using **Python (Flask)** and follows a modular structure for scalability and cloud deployment.

---

## 🧩 Features

- 🔍 **Automated Research Search:** Query academic data sources with filters (year range, keywords).  
- 📦 **Multi-format Output:** Generates JSON, CSV, SQLite, and BibTeX.  
- ⏰ **Task Scheduling:** Automate repeated searches via the frontend.  
- ☁️ **Cloud Ready:** Fully deployable on **Railway.app** with minimal configuration.  
- 🧠 **Modular Agents:** Each agent handles a specific function (fetching, extraction, storage, etc.).  
- 🧾 **API + CLI Access:** Run via HTTP API or command line for flexibility.  

---

## 🏗️ Folder Structure

```
aro_agent_backend/
│
├── .env                     # Environment variables (optional)
├── .gitignore               # Git ignore configuration
│
├── aro_agent/               # Main application package
│   ├── agents/              # Submodules responsible for automation logic
│   │   ├── coordinator.py   # Coordinates the entire research workflow
│   │   ├── discovery.py     # Discovers relevant academic sources
│   │   ├── extract.py       # Extracts structured data from results
│   │   ├── fetch.py         # Retrieves data via APIs or online services
│   │   ├── storage.py       # Saves results (CSV, JSON, SQLite, BibTeX)
│   │   └── __init__.py      # Initializes the agent package
│   │
│   ├── api.py               # Flask API for handling search & scheduling requests
│   ├── cli.py               # Command-line interface for local testing
│   ├── config.py            # Configuration settings (paths, constants, etc.)
│   ├── models.py            # Data models and schema definitions
│   ├── templates/assets/    # Static assets or templates for emails/reports
│   │
│   └── tests/               # ✅ Unit and integration tests
│       ├── test_primary_id.py              # DOI and arXiv ID cleaning tests
│       ├── test_api_schedule_toggle.py     # Schedule enable/disable tests
│       ├── test_zip_endpoint.py            # ZIP packaging endpoint tests
│       ├── test_send_email_mock.py         # Mock email sending tests
│       ├── test_storage_integrity.py       # (Optional) File save/load tests
│       └── __init__.py                     # Marks directory as a test package
│
└── requirements.txt         # Backend dependencies (Flask, requests, pytest, etc.)
```

---

## ⚙️ Installation & Setup (Local)

### 1. Navigate to backend folder
```bash
cd aro_agent_backend
```

### 2. Create and activate virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> If requirements.txt is missing, install manually:
```bash
pip install flask requests sqlite-utils
```

### 4. Run the backend API
```bash
cd aro_agent
python api.py
```

By default, the backend runs at:
```
http://127.0.0.1:5000/
```

---

## ☁️ Deployment on Railway

### 1. Upload `aro_agent_backend` folder
Go to [https://railway.app](https://railway.app) and create a new Flask project.

### 2. Add environment variables
```
FLASK_ENV=production
PORT=5000
```

### 3. Start command (in Railway settings)
```
python aro_agent/api.py
```

Once deployed, your live API will be available at:
```
https://aroagentbackend-production.up.railway.app
```

---

## 🧪 API Testing

### Test via CURL
```bash
curl -X POST https://yourdomain.up.railway.app/runs   -H "Content-Type: application/json"   -d '{"query":"machine learning fraud","per_source_limit":10,"from_year":2019,"to_year":2025}'
```

### Example JSON Response
```json
{
  "query": "machine learning fraud",
  "results": [...],
  "format": "json"
}
```

---

## 🧾 CLI Usage (Optional)

Run directly from the terminal without the frontend:
```bash
cd aro_agent_backend/aro_agent
python cli.py --query "artificial intelligence" --from_year 2020 --to_year 2025
```

Results are saved automatically in:
```
out/run_YYYYMMDD_HHMMSS/
```

Formats include:
- `.csv`
- `.json`
- `.sqlite`
- `.bib`
- `index.html` (static summary)

---

## 🧠 Architecture Summary

| Layer | Role |
|-------|------|
| **Coordinator** | Central controller managing workflow logic |
| **Discovery** | Identifies relevant research sources |
| **Fetch** | Retrieves and formats external data |
| **Extract** | Processes raw data into structured output |
| **Storage** | Persists outputs in multiple formats |
| **API / CLI** | Provides user access for web or terminal execution |

---

## ✅ Evidence of Execution

- Backend tested via local and Railway environments.  
- Verified response JSON for multiple queries (2019–2025 range).  
- Output stored under `/out/` directory in structured formats.  

---

## 👥 Author & Acknowledgments

**Developer:** Abdullah Khalfan Alshibli  
**Project:** Academic Research Online Agent (ARO Agent)  
**Institution:** Essex University  
**Unit:** Development Individual Project (Unit 11)  
**Supervisor:** Dr Sabeen Tahir  

---

## 📚 References

- Flask Framework — https://flask.palletsprojects.com/  
- Python 3.12 Documentation — https://docs.python.org/3/  
- Railway Deployment — https://docs.railway.app/  
- SQLite — https://www.sqlite.org/
