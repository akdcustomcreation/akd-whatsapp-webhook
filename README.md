# AKD WhatsApp Webhook

Webhook receiver for AKD Custom Creation WhatsApp Business messages (Meta Cloud API).

## Endpoints

- `GET /webhook` answers Meta's verification challenge.
- `POST /webhook` records inbound messages.
- `GET /health` returns `ok`.

## Configuration

Set the `WEBHOOK_VERIFY_TOKEN` environment variable to the same verify token
registered in the Meta app. The receiver also reads it from
`.webhook-verify-token` when the environment variable is not set.

## Run locally

```text
python3 webhook_receiver.py --host 127.0.0.1 --port 8765
```

## Deploy

- Render: this repo deploys as a Python web service from `render.yaml`
  (uses `webhook_receiver.py`).
- PythonAnywhere (free Beginner account, no card required): create a manual
  web app from this repo and point its WSGI file at `wsgi.py`, with the
  `WEBHOOK_VERIFY_TOKEN` environment variable set.
