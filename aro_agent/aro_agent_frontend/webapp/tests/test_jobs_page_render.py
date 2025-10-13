import types
import pytest
from webapp.app import APP as app

@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c

def _fake_response(json_obj, status=200):
    r = types.SimpleNamespace()
    r.ok = (status == 200)
    r.status_code = status
    r.headers = {"content-type": "application/json"}
    r.text = ""
    r.json = lambda: json_obj
    return r

def test_jobs_page(client, monkeypatch):
    """
    Tests that the jobs page displays job schedule status fetched from the backend.
    """
    def fake_get(url, timeout=None, **kwargs):
        if url.endswith("/jobs"):
            return _fake_response([
                {"job_id":"job_1","query":"ai research",
                 "schedule":{"enabled": True, "next": "2025-10-14T09:00:00Z"},
                 "runs":[{"id":"run_1"}]}
            ])
        return _fake_response({}, 404)

    monkeypatch.setattr("webapp.app.requests.get", fake_get)

    r = client.get("/jobs")
    assert r.status_code == 200
    assert b"ai research" in r.data
    assert b"Enabled" in r.data or b"enabled" in r.data
