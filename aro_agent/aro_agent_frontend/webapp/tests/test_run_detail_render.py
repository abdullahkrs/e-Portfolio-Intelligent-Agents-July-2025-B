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

def test_run_detail_page(client, monkeypatch):
    """
    Tests that the run detail page shows preview rows and artifact links.
    """
    def fake_get(url, timeout=None, **kwargs):
        if url.endswith("/runs/run_1"):
            return _fake_response({
                "meta": {"query": "ml fraud"},
                "links": {
                    "csv": "/out/run_1/results.csv",
                    "json": "/out/run_1/results.json",
                    "sqlite": "/out/run_1/results.sqlite",
                    "bibtex": "/out/run_1/results.bib",
                },
                "preview": {"columns":["title"], "rows":[["paper A"], ["paper B"]]},
                "schedule": {"enabled": False}
            })
        return _fake_response({}, 404)

    monkeypatch.setattr("webapp.app.requests.get", fake_get)

    r = client.get("/runs/run_1")
    assert r.status_code == 200
    assert b"paper A" in r.data and b"paper B" in r.data
    assert b"results.csv" in r.data and b"results.json" in r.data
