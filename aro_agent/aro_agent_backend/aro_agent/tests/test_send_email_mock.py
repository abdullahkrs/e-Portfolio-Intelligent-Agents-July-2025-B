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

def _seed_json(root: Path) -> Path:
    p = root / "results.json"
    p.write_text(json.dumps({"k":"v"}), encoding="utf-8")
    return p

def test_send_requires_recipient(client, tmp_path):
    """
    Tests that /send validates recipient emails.
    """
    artefacts_json = _seed_json(tmp_path)
    r = client.post("/send", json={
        "query": "demo",
        "artefacts": {"json": str(artefacts_json)},
        "mail_to": "",
        "attach_zip": False
    })
    assert r.status_code in (400, 422)

def test_send_success_with_mock(client, monkeypatch, tmp_path):
    """
    Tests that /send uses the mocked mailer and returns message id.
    """
    artefacts_json = _seed_json(tmp_path)

    def fake_build_and_send_email(**kwargs):
        return {"id": "test-message-id"}

    monkeypatch.setattr("aro_agent.api.build_and_send_email", fake_build_and_send_email)

    r = client.post("/send", json={
        "query": "demo",
        "artefacts": {"json": str(artefacts_json)},
        "mail_to": "user@example.com",
        "attach_zip": False
    })
    assert r.status_code == 200
    assert r.is_json and r.get_json().get("gmail_message_id") == "test-message-id"
