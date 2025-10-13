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

def test_homepage_lists_runs(client, monkeypatch):
    """
    Tests that the homepage correctly displays the list of runs from the backend.
    """
    def fake_get(url, timeout=None, **kwargs):
        if url.endswith("/runs"):
            return _fake_response([
                {"id":"run_1","query":"machine learning","counts":{"arxiv":2,"crossref":1},
                 "timestamp":"2025-10-01T10:00:00Z","new_items":1}
            ])
        return _fake_response({}, 404)

    monkeypatch.setattr("webapp.app.requests.get", fake_get)

    r = client.get("/")
    assert r.status_code == 200
    assert b"machine learning" in r.data
    assert b"run_1" in r.data
