# 🌐 ARO Agent — Frontend Web Interface (`aro_agent_frontend`)

## 📘 Overview
The **ARO Agent Frontend** is the user-facing web application for the *Academic Research Online Agent (ARO Agent)* project.  
It provides an intuitive interface that allows users to perform academic searches, view results, schedule research jobs, and interact seamlessly with the backend API.

Developed using **Python Flask**, **Jinja2 templates**, **HTML**, **CSS**, and **JavaScript**, it focuses on a clean, responsive, and accessible design.

---

## 🧩 Features

- 🎯 **User-friendly Interface** — Simplifies complex academic searches  
- 🔄 **Dynamic Results Display** — Automatically loads and formats API responses  
- 📅 **Scheduling System** — Allows users to enable or disable scheduled research jobs  
- 🌙 **Theme Toggle** — Light/Dark/Auto display modes  
- ☁️ **Cloud Deployable** — Fully compatible with **Railway** for public access  
- 🧩 **Backend Integration** — Communicates directly with `aro_agent_backend` API  

---

## 🏗️ Folder Structure

```
aro_agent_frontend/
│
├── .env                          # Environment configuration (optional)
├── .gitignore                    # Files ignored by Git
├── railway.json                  # Railway deployment configuration
├── requirements.txt              # Flask and web dependencies (Flask, requests, pytest)
│
├── webapp/                       # Main Flask application package
│   ├── app.py                    # Application entry point (Flask routes, logic)
│   ├── __init__.py               # Flask app factory initialization
│   │
│   ├── static/                   # Frontend static resources (CSS, JS, images)
│   │   └── style.css             # Main CSS file for layout and themes
│   │
│   ├── templates/                # Jinja2 templates for rendering pages
│   │   ├── layout.html           # Shared layout (navbar, footer, theme toggle)
│   │   ├── index.html            # Homepage — Search interface + recent runs
│   │   ├── results.html          # Results page — displays preview table
│   │   ├── schedule.html         # Page for scheduled jobs  (Not Used)
│   │   └── schedule_missing.html # Placeholder when schedule data unavailable  (Not Used)
│   │
│   ├── tests/                    # ✅ Frontend test suite
│   │   ├── test_homepage_render.py      # Tests homepage run list rendering
│   │   ├── test_run_detail_render.py    # Tests run detail and preview table
│   │   ├── test_jobs_page_render.py     # Tests jobs schedule page
│   │   └── __init__.py                  # Marks directory as a test package
│   │
│   └── __pycache__/              # Compiled Python cache files (auto-generated)
│
└── wsgi.py                       # WSGI entrypoint for Railway/cloud deployment
```

---

## ⚙️ Installation & Local Setup

### 1. Navigate to the frontend directory
```bash
cd aro_agent_frontend
```

### 2. Create and activate a virtual environment
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

### 4. Run the frontend web application
```bash
cd webapp
python app.py
```

The app will start locally on:
```
http://127.0.0.1:8000/
```

---

## 🔗 Connecting to Backend API

The frontend communicates with the **ARO Agent Backend** through RESTful API calls.  
By default, it targets the backend at:

```
http://127.0.0.1:5000/
```

If your backend is deployed on **Railway**, update your environment variable or configuration file (e.g., `.env` or inside `app.py`) to:

```
https://yourdomain.up.railway.app
```

---

## ☁️ Deployment on Railway (Cloud)

### 1. Create a new Flask project on [Railway.app](https://railway.app)
Upload the `aro_agent_frontend` folder.

### 2. Add Environment Variables
```
FLASK_ENV=production
PORT=8000
```

### 3. Define the Start Command
```
python webapp/app.py
```

### 4. Link to Backend
Ensure the `app.py` in `webapp` points to your backend API URL:
```python
BACKEND_URL = "https://yourdomain.up.railway.app"
```

After deployment, your frontend will be publicly accessible at a Railway URL such as:
```
https://yourdomain.up.railway.app
```

---

## 🧪 Testing & Verification

1. **Search Test**
   - Visit the homepage and enter a query (e.g., *machine learning ethics*).  
   - Verify that the results are displayed in a responsive table.  

2. **Schedule Test**
   - Enable or disable a scheduled job.
   - Confirm that it appears in the schedule list.

3. **Backend Connection**
   - The network tab in browser DevTools should show successful API calls to your backend endpoint.

---

## 🧠 Architecture Overview

| Component | Description |
|------------|-------------|
| **Frontend (Flask)** | Hosts HTML templates, handles routes, and communicates with backend |
| **Backend (API)** | Processes queries and returns structured data |
| **Templates (Jinja2)** | Rendered dynamically to present search results and schedules |
| **Static Assets** | Contain CSS and JS to manage layout, theme, and responsiveness |

---

## ✅ Evidence of Execution

- Successfully runs locally (`localhost:8000`) and on **Railway cloud**  
- Verified connection with backend API returning real JSON results  
- UI confirmed functional for searching and viewing schedules  

---

## 👥 Author & Acknowledgments

**Developer:** Abdullah Khalfan Alshibli  
**Project:** Academic Research Online Agent (ARO Agent)  
**Institution:** Essex University  
**Unit:** Development Individual Project (Unit 11)  
**Supervisor:** Dr Sabeen Tahir  

---

## 📚 References

- Flask Web Framework: https://flask.palletsprojects.com/  
- Railway Deployment: https://docs.railway.app/  
- Jinja2 Templating: https://jinja.palletsprojects.com/  
- Python 3.12 Documentation: https://docs.python.org/3/
