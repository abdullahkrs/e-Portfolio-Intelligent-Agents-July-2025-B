import json
from pathlib import Path
import pytest
from aro_agent.api import app as flask_app

@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ARO_OUT_ROOT", str(tmp_path))
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as c:
        yield c

def _seed_run(root: Path, name="run_20250101_010101") -> Path:
    run = root / name
    run.mkdir(parents=True, exist_ok=True)
    # minimal artefacts
    (run / "results.csv").write_text("csv")
    (run / "results.json").write_text("{}")
    (run / "results.sqlite").write_text("db")
    (run / "results.bib").write_text("bib")
    (run / "run.json").write_text(json.dumps({"meta": {"query":"demo"}, "links": {}}))
    return run

def test_zip_success(client, tmp_path):
    """
    Tests that the /zip endpoint returns a ZIP stream with correct headers.
    """
    run = _seed_run(tmp_path)
    payload = {"artefacts": {
        "csv": str(run / "results.csv"),
        "json": str(run / "results.json"),
        "sqlite": str(run / "results.sqlite"),
        "bibtex": str(run / "results.bib"),
    }}
    r = client.post("/zip", json=payload)
    assert r.status_code == 200
    assert "application/zip" in (r.headers.get("Content-Type") or r.headers.get("content-type") or "")
    cd = (r.headers.get("Content-Disposition") or r.headers.get("content-disposition") or "").lower()
    assert "filename=" in cd

def test_zip_requires_payload(client):
    """
    Tests that /zip returns 400 when the JSON body is missing/invalid.
    """
    r = client.post("/zip", json={})
    assert r.status_code in (400, 422)
