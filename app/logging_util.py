"""Structured JSON logging + request_id middleware."""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, g, request


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        rid = getattr(record, "request_id", None)
        if not rid:
            try:
                rid = getattr(g, "request_id", None)
            except RuntimeError:
                rid = None
        if rid:
            payload["request_id"] = rid
        for key in ("path", "method", "status", "duration_ms", "remote_addr"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.request_id = getattr(g, "request_id", None)
        except RuntimeError:
            record.request_id = None
        return True


def configure_logging(app: Flask) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    root = logging.getLogger()
    if not any(
        isinstance(h, logging.StreamHandler)
        and isinstance(getattr(h, "formatter", None), JsonFormatter)
        for h in root.handlers
    ):
        root.handlers.clear()
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    app.logger.handlers = list(root.handlers)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False


def register_request_logging(app: Flask) -> None:
    @app.before_request
    def _assign_request_id():
        incoming = request.headers.get("X-Request-ID") or request.headers.get("X-Request-Id")
        g.request_id = (incoming or uuid.uuid4().hex)[:32]
        g._req_started = time.perf_counter()

    @app.after_request
    def _log_request(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        started = getattr(g, "_req_started", None)
        duration_ms = round((time.perf_counter() - started) * 1000, 2) if started else None
        app.logger.info(
            "request",
            extra={
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "remote_addr": request.headers.get("X-Forwarded-For", request.remote_addr),
            },
        )
        return response
