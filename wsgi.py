# WSGI entry point for PythonAnywhere (free tier, no card required).
#
# Same behaviour as webhook_receiver.py, adapted for WSGI:
#   GET  /webhook -> answers Meta's verification challenge
#   POST /webhook -> records inbound messages, answers EVENT_RECEIVED
#   GET  /health  -> returns ok
#
# The verify token comes from the WEBHOOK_VERIFY_TOKEN environment variable,
# set in the PythonAnywhere web app configuration.

import json
import os
from urllib.parse import parse_qs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(BASE_DIR, "inbox")
EVENTS_PATH = os.path.join(INBOX_DIR, "events.jsonl")
MESSAGES_PATH = os.path.join(INBOX_DIR, "messages.jsonl")


def _verify_token():
    return os.environ.get("WEBHOOK_VERIFY_TOKEN", "").strip()


def _append(path, obj):
    os.makedirs(INBOX_DIR, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(obj, ensure_ascii=False) + "\n")


def application(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")

    if method == "GET" and path == "/health":
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"ok"]

    if method == "GET" and path == "/webhook":
        query = parse_qs(environ.get("QUERY_STRING", ""))
        mode = query.get("hub.mode", [""])[0]
        token = query.get("hub.verify_token", [""])[0]
        challenge = query.get("hub.challenge", [""])[0]
        if mode == "subscribe" and token and token == _verify_token():
            start_response("200 OK", [("Content-Type", "text/plain")])
            return [challenge.encode("utf-8")]
        start_response("403 Forbidden", [("Content-Type", "text/plain")])
        return [b"Forbidden"]

    if method == "POST" and path == "/webhook":
        try:
            length = int(environ.get("CONTENT_LENGTH", "0") or 0)
        except ValueError:
            length = 0
        raw = environ["wsgi.input"].read(length) if length > 0 else b""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (ValueError, UnicodeDecodeError):
            payload = {"_raw": raw.decode("utf-8", "replace")}
        _append(EVENTS_PATH, payload)
        for entry in payload.get("entry", []) if isinstance(payload, dict) else []:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    _append(MESSAGES_PATH, message)
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"EVENT_RECEIVED"]

    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"Not Found"]
