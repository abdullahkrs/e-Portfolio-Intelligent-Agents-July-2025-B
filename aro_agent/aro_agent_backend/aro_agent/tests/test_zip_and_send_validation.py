# aro_agent_backend/aro_agent/tests/test_zip_and_send_validation.py
from __future__ import annotations
import os, json
from pathlib import Path
from fastapi.testclient import TestClient
from aro_agent.api import app

def make_client(tmp_out: Path) -> TestClient:
    os.environ["ARO_OUT_ROOT"] = str(tmp_out)
    tmp_out.mkdir(parents=True, exist_ok=True)
    return TestClient(app)

def _seed_run(tmp_out: Path, name="run_20250101_010101") -> Path:
    run = tmp_out / name
    run.mkdir(parents=True, exist_ok=True)
    # minimal run.json + artifacts
    (run / "run.json").write_text(json.dumps({"meta": {"query":"demo"}, "links": {}}), "utf-8")
    for f in ("results.csv","results.json","results.sqlite","results.bib"):
        (run / f).write_text("x", "utf-8")
    return run

def test_zip_missing_json_returns_400(tmp_path):
    client = make_client(tmp_path)
    r = client.post("/zip", json={"artefacts": {"csv": "x.csv"}})
    assert r.status_code == 400

def test_zip_success(tmp_path):
    client = make_client(tmp_path)
    run = _seed_run(tmp_path)
    payload = {"artefacts": {
        "csv": str(run / "results.csv"),
        "json": str(run / "results.json"),
        "sqlite": str(run / "results.sqlite"),
        "bibtex": str(run / "results.bib"),
    }}
    r = client.post("/zip", json=payload)
    assert r.status_code == 200
    # should stream a file named aro_results.zip from the run dir
    assert r.headers.get("content-disposition", "").lower().endswith('filename="aro_results.zip"')

def test_send_requires_recipient(tmp_path, monkeypatch):
    client = make_client(tmp_path)
    run = _seed_run(tmp_path)

    # Patch the Gmail sender so the test doesn't touch external services
    def fake_build_and_send_email(**kwargs):
        return {"id": "test-message-id"}
    monkeypatch.setattr("aro_agent.api.build_and_send_email", fake_build_and_send_email)

    # Missing recipients → 400
    r = client.post("/send", json={
        "query": "demo",
        "artefacts": {"json": str(run / "results.json")},
        "mail_to": "",
        "attach_zip": False
    })
    assert r.status_code == 400

    # Valid recipients → 200, returns a message id
    r2 = client.post("/send", json={
        "query": "demo",
        "artefacts": {"json": str(run / "results.json")},
        "mail_to": "user@example.com",
        "attach_zip": False
    })
    assert r2.status_code == 200
    assert r2.json().get("gmail_message_id") == "test-message-id"
