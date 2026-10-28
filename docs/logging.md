# Structured logging

## What we emit

Each HTTP request logs one JSON line (stdout), for example:

```json
{"ts":"2026-10-29T01:00:00+00:00","level":"INFO","logger":"app","msg":"request","request_id":"abc...","method":"GET","path":"/shop","status":200,"duration_ms":7.2}
```

- `request_id`: from inbound `X-Request-ID` or a new UUID; echoed on the response header.
- Implemented in `app/logging_util.py`, wired in `create_app()`.

Ops scripts (`scripts/*.py`) print their own JSON lines with an `event` field (`refresh_start`, `stock_anomaly`, …).

## Shipping to Loki / ELK in production (sketch)

1. Run the app under gunicorn/uwsgi; keep logs on **stdout only** (12-factor).
2. **Loki**: Promtail / Alloy scrape container stdout → Loki; Grafana explores by `request_id`.
3. **ELK**: Filebeat/Fluent Bit → Logstash or Elasticsearch ingest pipeline; index `mall-app-*`.
4. Correlate: pass `X-Request-ID` from gateway → app → DB slow-query logs.
5. Do **not** log secrets, passwords, or full card data.

Local demo: start Flask and watch JSON lines in the console.
