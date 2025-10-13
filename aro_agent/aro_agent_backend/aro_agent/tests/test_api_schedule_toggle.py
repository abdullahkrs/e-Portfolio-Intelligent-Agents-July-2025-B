import json, os
from pathlib import Path
import pytest
from aro_agent.api import app as flask_app

@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Isolate OUT root per test
    monkeypatch.setenv("ARO_OUT_ROOT", str(tmp_path))
    flask_app.config.update(TESTING=True)
    with flask_app.test_client() as c:
        yield c

def _seed_run(root: Path, name="run_20250101_000000") -> Path:
    run_dir = root / name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.json").write_text(json.dumps({
        "meta": {"query": "ml fraud", "from_year": 2019, "to_year": 2025},
        "links": {}
    }), encoding="utf-8")
    return run_dir

def test_schedule_enable_and_disable(client, tmp_path):
    """
    Tests that scheduling can be enabled and disabled for a run.
    """
    run_dir = _seed_run(tmp_path)
    run_id = run_dir.name

    # Enable
    r1 = client.post(f"/runs/{run_id}/schedule/enable")
    assert r1.status_code == 200
    assert (run_dir / "SCHEDULE.txt").exists()

    # Disable
    r2 = client.post(f"/runs/{run_id}/schedule/disable")
    assert r2.status_code == 200
    assert not (run_dir / "SCHEDULE.txt").exists()

def test_list_runs_and_jobs_empty(client):
    """
    Tests that /runs and /jobs return empty arrays when nothing exists.
    """
    r = client.get("/runs")
    assert r.status_code == 200 and r.is_json
    assert r.get_json() == []

    rj = client.get("/jobs")
    assert rj.status_code == 200 and rj.is_json
    assert rj.get_json() == []
