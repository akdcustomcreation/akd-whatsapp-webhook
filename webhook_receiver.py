#!/usr/bin/env python3
"""Webhook receiver for AKD Custom Creation WhatsApp Business messages.

Listens for Meta webhook calls for the WhatsApp Business Cloud API.

  GET  /webhook?hub.mode=subscribe&hub.verify_token=<TOKEN>&hub.challenge=<C>
       Answers Meta's verification challenge when the token matches.
  POST /webhook
       Appends the raw event to inbox/events.jsonl and each inbound text
       message to inbox/messages.jsonl, then answers 200.

Run:  python3 webhook_receiver.py [--port 8765] [--host 127.0.0.1]
The verify token is read from .webhook-verify-token next to this file.
It is the same token registered as the webhook verify token in the Meta app.

Signature checking against X-Hub-Signature-256 needs the Meta App Secret,
which is not stored here. Add it only through the secure credential flow
if signature verification is required later.
"""
import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
CONNECTOR_DIR = os.path.dirname(HERE)
INBOX_DIR = os.path.join(CONNECTOR_DIR, "inbox")
TOKEN_FILE = os.path.join(CONNECTOR_DIR, ".webhook-verify-token")


def load_verify_token():
    env_token = os.environ.get("WEBHOOK_VERIFY_TOKEN", "").strip()
    if env_token:
        return env_token
    if not os.path.exists(TOKEN_FILE):
        sys.stderr.write("verify token file missing: " + TOKEN_FILE + "\n")
        sys.exit(1)
    with open(TOKEN_FILE, "r", encoding="utf-8") as handle:
        return handle.read().strip()


VERIFY_TOKEN = load_verify_token()


def append_jsonl(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send(200, "ok", "text/plain")
            return
        if parsed.path == "/webhook":
            query = parse_qs(parsed.query)
            mode = query.get("hub.mode", [""])[0]
            token = query.get("hub.verify_token", [""])[0]
            challenge = query.get("hub.challenge", [""])[0]
            if mode == "subscribe" and token and hmac.compare_digest(token, VERIFY_TOKEN):
                self._send(200, challenge, "text/plain")
            else:
                self._send(403, "forbidden", "text/plain")
            return
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/webhook":
            self._send(404, "not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", 0) or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            event = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            event = {"raw_unparsed": raw.decode("utf-8", "replace")}
        now = datetime.now(timezone.utc).isoformat()
        append_jsonl(
            os.path.join(INBOX_DIR, "events.jsonl"),
            {"received_at": now, "signature": self.headers.get("X-Hub-Signature-256", ""), "event": event},
        )
        for entry in event.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    append_jsonl(
                        os.path.join(INBOX_DIR, "messages.jsonl"),
                        {
                            "received_at": now,
                            "from": message.get("from", ""),
                            "message_id": message.get("id", ""),
                            "timestamp": message.get("timestamp", ""),
                            "type": message.get("type", ""),
                            "text": (message.get("text") or {}).get("body", ""),
                        },
                    )
        self._send(200, "EVENT_RECEIVED", "text/plain")

    def _send(self, code, body, content_type):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    parser = argparse.ArgumentParser(description="WhatsApp webhook receiver")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"listening on {args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
