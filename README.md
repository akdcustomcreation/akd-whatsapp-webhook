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

This repo is deployed on Render as a Python web service from `render.yaml`.
