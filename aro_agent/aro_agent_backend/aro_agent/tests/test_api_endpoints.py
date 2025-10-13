# aro_agent_backend/aro_agent/tests/test_api_endpoints.py
from __future__ import annotations
import os, json, tempfile
from pathlib import Path
from fastapi.testclient import TestClient

# Import the FastAPI app
from aro_agent.api import app, OUT_ROOT

def make_client(tmp_out: Path) -> TestClient:
    # Point the API to a fresh, isolated OUT dir
    os.environ["ARO_OUT_ROOT"] = str(tmp_out)
    tmp_out.mkdir(parents=True, exist_ok=True)
    return TestClient(app)

def test_list_runs_empty(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/runs")
    assert r.status_code == 200
    assert r.json() == []  # no runs yet

def test_get_run_404(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/runs/run_9999")
    assert r.status_code == 404

def test_jobs_empty(tmp_path):
    client = make_client(tmp_path)
    r = client.get("/jobs")
    assert r.status_code == 200
    assert r.json() == []  # no jobs yet

def test_enable_disable_run_schedule(tmp_path):
    # Create a fake run dir with run.json + schedule.txt
    client = make_client(tmp_path)
    run_dir = tmp_path / "run_20250101_000000"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps({
        "meta": {"query": "ml fraud", "from_year": 2019, "to_year": 2025,
                 "sources_enabled": {"arxiv": True}},
        "links": {}
    }), encoding="utf-8")

    # Enable schedule writes SCHEDULE.txt
    r = client.post(f"/runs/{run_dir.name}/schedule/enable")
    assert r.status_code == 200
    assert (run_dir / "SCHEDULE.txt").exists()

    # Disable removes SCHEDULE.txt
    r = client.post(f"/runs/{run_dir.name}/schedule/disable")
    assert r.status_code == 200
    assert not (run_dir / "SCHEDULE.txt").exists()
