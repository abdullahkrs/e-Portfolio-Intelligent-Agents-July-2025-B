# wsgi.py
import importlib, os

# Load your Flask WSGI app (unchanged)
APP_MODULE = os.getenv("APP_MODULE", "webapp.app:APP")
module_name, attr = APP_MODULE.split(":", 1)
module = importlib.import_module(module_name)
app = getattr(module, attr)  # <-- this is the Flask WSGI app

# ---- NEW: wrap WSGI -> ASGI for Uvicorn ----
from asgiref.wsgi import WsgiToAsgi
asgi_app = WsgiToAsgi(app)

# Optional: add a basic health check on the WSGI app
try:
    from flask import Flask
    if isinstance(app, Flask):
        if not any(r.rule == "/healthz" for r in app.url_map.iter_rules()):
            @app.route("/healthz")
            def _healthz():
                return "ok", 200
except Exception:
    pass
