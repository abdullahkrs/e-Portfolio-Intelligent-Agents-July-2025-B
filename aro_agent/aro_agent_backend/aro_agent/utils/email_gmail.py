# aro_agent/utils/email_gmail.py
import os, json, mimetypes, base64
from typing import Iterable
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

def _json_from_env(raw_key: str) -> dict | None:
    raw = (os.environ.get(raw_key) or "").strip()
    if raw:
        return json.loads(raw)
    return None

def _merge_client_info(token_info: dict, client_info: dict | None) -> dict:
    if token_info is None:
        return {}
    need_id = "client_id" not in token_info
    need_secret = "client_secret" not in token_info
    need_token_uri = "token_uri" not in token_info
    if client_info and (need_id or need_secret or need_token_uri):
        section = client_info.get("installed") or client_info.get("web") or {}
        token_info = dict(token_info)
        if need_id and "client_id" in section:
            token_info["client_id"] = section["client_id"]
        if need_secret and "client_secret" in section:
            token_info["client_secret"] = section["client_secret"]
        if need_token_uri and "token_uri" in section:
            token_info["token_uri"] = section["token_uri"]
    if not token_info.get("scopes"):
        token_info["scopes"] = SCOPES
    return token_info

def _load_credentials(credentials_path: str = "google_client_credentials.json",
                      token_path: str = "google_token.json") -> Credentials:
    # Prefer env JSON
    token = _json_from_env("GOOGLE_TOKEN_JSON")
    client = _json_from_env("GOOGLE_CLIENT_CREDENTIALS_JSON")

    if token:
        info = _merge_client_info(token, client)
    elif os.path.isfile(token_path):
        with open(token_path, "r", encoding="utf-8") as f:
            info = json.load(f)
        info = _merge_client_info(info, client)
    else:
        raise RuntimeError("No Gmail token JSON found in env or file.")

    creds = Credentials.from_authorized_user_info(info, scopes=SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise RuntimeError("Gmail credentials invalid and no refresh token available.")
    return creds

def _add_attachment(msg: EmailMessage, path: str):
    ctype, _ = mimetypes.guess_type(path)
    maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
    with open(path, "rb") as f:
        msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(path))

def send_email(
    sender: str,
    to: Iterable[str] | str,
    subject: str,
    html_body: str,
    attachments: list[str] | None = None,
    credentials_path: str = "google_client_credentials.json",  # ignored when env is present
    token_path: str = "google_token.json",                      # ignored when env is present
):
    creds = _load_credentials(credentials_path, token_path)
    service = build("gmail", "v1", credentials=creds)

    if isinstance(to, str):
        to = [to]

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content("This is a MIME email.")
    msg.add_alternative(html_body, subtype="html")

    for p in attachments or []:
        if p and os.path.isfile(p):
            _add_attachment(msg, p)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"id": result.get("id")}
