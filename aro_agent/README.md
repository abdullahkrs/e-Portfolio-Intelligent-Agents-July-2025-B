# 🧠 Academic Research Online Agent (ARO Agent)

## 📘 Overview
**ARO Agent** is an **intelligent research automation tool** that enables users to perform structured academic literature searches, process research results, and visualize findings efficiently.  
It was developed as part of the **Development Individual Project (Unit 11)** following the **Design Proposal from Unit 6**.

The system automates academic research retrieval, scheduling, and report generation using a modular architecture — combining a **Flask-based backend API** with a **responsive web frontend** built using **Jinja templates, HTML, CSS, and JavaScript**.

---

## ⚙️ System Components

| Component | Description | Framework / Tech |
|------------|--------------|------------------|
| **aro_agent_backend** | Backend API that handles search, scheduling, and data export (JSON, CSV, SQLite, BibTeX). | Python (Flask), Requests, SQLite |
| **aro_agent_frontend** | Frontend web interface that interacts with the backend API, allowing users to run, schedule, and view results. | HTML, CSS, JS (Jinja templates) |
| **aro_agent_core** | Core logic (within scaffold) coordinating API calls, result parsing, and file generation. | Python |

---

## 🏗️ Project Structure

The project is organized into two main components — the **Backend API** and the **Frontend Web Interface** — each functioning independently but integrated through RESTful communication.

```
aro_agent/
│
├── aro_agent_backend/                 # Backend API (Flask)
│   ├── .env                          # Environment configuration (API keys, database paths)
│   ├── .gitignore                    # Ignored files for version control
│   ├── aro_agent/                    # Core backend package
│   │   ├── agents/                   # Main agent modules handling automation and processing
│   │   │   ├── coordinator.py        # Coordinates full research workflow (query → results)
│   │   │   ├── discovery.py          # Finds relevant sources and metadata
│   │   │   ├── extract.py            # Extracts structured data from retrieved content
│   │   │   ├── fetch.py              # Fetches data from APIs or local sources
│   │   │   ├── storage.py            # Handles saving to JSON, SQLite, CSV, BibTeX
│   │   │   └── __init__.py           # Package initializer
│   │   ├── api.py                    # REST API routes for research queries
│   │   ├── cli.py                    # Command-line interface for local runs and testing
│   │   ├── config.py                 # Configuration (paths, limits, and global settings)
│   │   ├── models.py                 # Defines internal data models and schemas
│   │   └── templates/assets/         # Static assets and templates for email/report generation
│
├── aro_agent_frontend/               # Web user interface (Flask + Jinja)
│   ├── .env                          # Frontend environment configuration
│   ├── .gitignore                    # Version control ignore file
│   ├── railway.json                  # Railway deployment configuration file
│   ├── README.md                     # Frontend-specific documentation
│   ├── requirements.txt              # Dependencies for web frontend
│   ├── webapp/                       # Main web application folder
│   │   ├── app.py                    # Entry point of the web application
│   │   ├── __init__.py               # Flask initialization
│   │   ├── static/style.css          # Application styling and layout
│   │   ├── templates/                # HTML templates (Jinja2)
│   │   │   ├── index.html            # Homepage (search interface)
│   │   │   ├── layout.html           # Shared base layout (header, theme toggle)
│   │   │   ├── results.html          # Displays research results in table format
│   │   │   ├── schedule.html         # Lists and manages scheduled jobs (Not Used)
│   │   │   └── schedule_missing.html # Fallback template when schedule not found  (Not Used)
│   └── wsgi.py                       # WSGI entrypoint for cloud deployment
│
└── (Root Directory)
    └── aro_agent
```

### 🧠 Summary of Responsibilities

| Layer | Folder | Purpose |
|-------|---------|----------|
| **Backend** | `aro_agent_backend/aro_agent/` | Implements the ARO Agent’s search, analysis, and scheduling API. |
| **Frontend** | `aro_agent_frontend/webapp/` | Provides a user-friendly web interface to access and visualize backend data. |
| **Deployment** | `.env`, `railway.json`, `requirements.txt` | Manage configuration and Railway deployment. |

---

## ⚙️ Installation Guide

### 🧩 Backend Setup — `aro_agent_backend`

#### 1. Navigate to backend directory
```bash
cd aro_agent_backend
```

#### 2. Create a virtual environment
```bash
python -m venv venv
```

Activate it:
```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

#### 3. Install dependencies
If your backend includes `requirements.txt`:
```bash
pip install -r requirements.txt
```
If not, install manually:
```bash
pip install flask requests sqlite-utils
```

#### 4. Run the backend server
```bash
cd aro_agent
python api.py
```

Backend runs by default on:
```
http://127.0.0.1:5000/
```

#### 5. Test API locally
```bash
curl -X POST http://127.0.0.1:5000/runs   -H "Content-Type: application/json"   -d '{"query": "machine learning fraud", "from_year": 2019, "to_year": 2025}'
```

---

### 🌐 Frontend Setup — `aro_agent_frontend`

#### 1. Navigate to frontend directory
```bash
cd aro_agent_frontend
```

#### 2. Create and activate virtual environment
```bash
python -m venv venv
```

Activate it:
```bash
# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Run the frontend app
```bash
cd webapp
python app.py
```

Frontend runs by default on:
```
http://127.0.0.1:8000/
```

#### 5. Connect to backend
Ensure the backend is already running locally or update configuration to your deployed Railway API endpoint, for example:
```
https://yourdomain.up.railway.app
```

---

## ☁️ Deployment on Railway (Cloud)

You can deploy both components separately on [Railway.app](https://railway.app/).

Each service must include:
- `requirements.txt`
- Startup command (`python app.py` or `python webapp/app.py`)
- Environment variables, e.g.:
```
FLASK_ENV=production
PORT=5000
```

### Example Startup Commands
**Backend:**
```
python aro_agent/api.py
```

**Frontend:**
```
python webapp/app.py
```

### Test Deployment
```bash
curl -X POST https://yourdomain.up.railway.app/runs   -H "Content-Type: application/json"   -d '{"query":"machine learning fraud","per_source_limit":10,"from_year":2019,"to_year":2025}'
```

---

## 🧪 Testing and Results

- Successful API runs produce results in `/out/run_YYYYMMDD_HHMMSS/`
- Generated files include `.csv`, `.json`, `.sqlite`, `.bib`, and static HTML reports
- Frontend dynamically displays results and schedules

---

## 🎓 Academic Relevance

This project demonstrates:
- Full-cycle **software development** and **deployment**
- Integration of **research automation**, **cloud services**, and **intelligent agents**
- Focus on **maintainability**, **scalability**, and **usability**

---

## 👥 Author & Acknowledgments

**Developer:** Abdullah Khalfan Alshibli  
**Project:** Academic Research Online Agent (ARO Agent)  
**Institution:** Essex University  
**Unit:** Development Individual Project (Unit 11)  
**Supervisor:** Dr Sabeen Tahir  

---

## 📚 References

- Flask Documentation: https://flask.palletsprojects.com/  
- Railway Deployment Guide: https://docs.railway.app/  
- Python 3.12 Reference: https://docs.python.org/3/  
- SQLite Database: https://www.sqlite.org/
