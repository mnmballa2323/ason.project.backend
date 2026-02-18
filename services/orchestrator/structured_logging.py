"""
Structured Logging — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
JSON-formatted logs with correlation IDs, tenant context, and trace IDs.
"""

import json
import logging
import os
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional


# ============================================================================
#  CONTEXT VARIABLES (async-safe per-request context)
# ============================================================================

_request_id: ContextVar[str] = ContextVar("request_id", default="")
_tenant_id: ContextVar[str] = ContextVar("tenant_id", default="")
_user_id: ContextVar[str] = ContextVar("user_id", default="")
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_span_id: ContextVar[str] = ContextVar("span_id", default="")


def set_request_context(
    request_id: str = None,
    tenant_id: str = "",
    user_id: str = "",
    trace_id: str = None,
    span_id: str = None,
):
    """Set per-request context for structured logging. Call at request start."""
    _request_id.set(request_id or str(uuid.uuid4())[:12])
    _tenant_id.set(tenant_id)
    _user_id.set(user_id)
    _trace_id.set(trace_id or str(uuid.uuid4()))
    _span_id.set(span_id or str(uuid.uuid4())[:16])


def get_request_context() -> Dict[str, str]:
    """Get current request context."""
    return {
        "request_id": _request_id.get(),
        "tenant_id": _tenant_id.get(),
        "user_id": _user_id.get(),
        "trace_id": _trace_id.get(),
        "span_id": _span_id.get(),
    }


# ============================================================================
#  JSON LOG FORMATTER
# ============================================================================

class StructuredFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON for machine parsing.

    Output format:
    {
      "timestamp": "2025-02-16T18:42:00.000Z",
      "level": "INFO",
      "logger": "qwen.orchestrator",
      "message": "Verification job completed",
      "request_id": "a1b2c3d4e5f6",
      "tenant_id": "tenant-uuid",
      "user_id": "user-uuid",
      "trace_id": "trace-uuid",
      "span_id": "span-hex",
      "service": "orchestrator",
      "hostname": "ason-orchestrator-0",
      "pid": 1234,
      "duration_ms": 142.5,
      "extra": {...}
    }
    """

    def __init__(self, service_name: str = "orchestrator"):
        super().__init__()
        self.service_name = service_name
        self.hostname = os.getenv("HOSTNAME", os.getenv("COMPUTERNAME", "localhost"))
        self.pid = os.getpid()

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "hostname": self.hostname,
            "pid": self.pid,
        }

        # Add request context (if available)
        ctx = get_request_context()
        if ctx["request_id"]:
            log_entry["request_id"] = ctx["request_id"]
        if ctx["tenant_id"]:
            log_entry["tenant_id"] = ctx["tenant_id"]
        if ctx["user_id"]:
            log_entry["user_id"] = ctx["user_id"]
        if ctx["trace_id"]:
            log_entry["trace_id"] = ctx["trace_id"]
        if ctx["span_id"]:
            log_entry["span_id"] = ctx["span_id"]

        # Add exception info
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Unknown",
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields (passed via logger.info("msg", extra={...}))
        standard_attrs = {
            "name", "msg", "args", "created", "relativeCreated", "thread",
            "threadName", "msecs", "pathname", "filename", "module",
            "funcName", "lineno", "exc_info", "exc_text", "stack_info",
            "levelname", "levelno", "message", "taskName",
        }
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in standard_attrs and not k.startswith("_")
        }
        if extras:
            log_entry["extra"] = extras

        # Source location (debug and error levels)
        if record.levelno >= logging.WARNING:
            log_entry["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_entry, default=str, separators=(",", ":"))


# ============================================================================
#  LOG SETUP
# ============================================================================

def setup_structured_logging(
    service_name: str = "orchestrator",
    log_level: str = None,
    output: str = "stdout",
):
    """
    Configure structured JSON logging for the application.

    Args:
        service_name: Name of the service (appears in every log line)
        log_level: Override log level (default: from ASON_LOG_LEVEL env)
        output: "stdout" or file path
    """
    level = getattr(logging, (log_level or os.getenv("ASON_LOG_LEVEL", "INFO")).upper(), logging.INFO)

    formatter = StructuredFormatter(service_name)

    # Configure handler
    if output == "stdout":
        handler = logging.StreamHandler(sys.stdout)
    else:
        handler = logging.FileHandler(output)

    handler.setFormatter(formatter)
    handler.setLevel(level)

    # Set root logger
    root = logging.getLogger()
    root.setLevel(level)
    # Remove existing handlers to avoid duplicates
    root.handlers.clear()
    root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ["uvicorn.access", "httpx", "httpcore", "asyncio"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    logging.getLogger("qwen").info(
        "Structured logging initialized",
        extra={"service": service_name, "level": level},
    )


# ============================================================================
#  REQUEST LOGGING MIDDLEWARE (FastAPI)
# ============================================================================

class RequestLoggingMiddleware:
    """
    FastAPI middleware that:
    1. Generates request_id and sets context
    2. Logs request start/end with duration
    3. Adds X-Request-ID header to response
    """

    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("qwen.http")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        start = time.time()
        request_id = str(uuid.uuid4())[:12]

        # Extract tenant from headers (set by auth middleware)
        headers_dict = dict(scope.get("headers", []))
        tenant_id = headers_dict.get(b"x-tenant-id", b"").decode()
        user_id = headers_dict.get(b"x-user-id", b"").decode()

        set_request_context(
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

        path = scope.get("path", "")
        method = scope.get("method", "")

        self.logger.info(
            f"{method} {path}",
            extra={"event": "request_start", "method": method, "path": path},
        )

        # Intercept response to capture status code
        response_status = [200]

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                response_status[0] = message.get("status", 200)
                # Inject X-Request-ID header
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            self.logger.error(
                f"{method} {path} 500",
                extra={
                    "event": "request_error",
                    "method": method, "path": path,
                    "status": 500, "duration_ms": round(duration_ms, 2),
                    "error": str(e),
                },
            )
            raise
        else:
            duration_ms = (time.time() - start) * 1000
            log_fn = self.logger.info if response_status[0] < 400 else self.logger.warning
            log_fn(
                f"{method} {path} {response_status[0]}",
                extra={
                    "event": "request_end",
                    "method": method, "path": path,
                    "status": response_status[0],
                    "duration_ms": round(duration_ms, 2),
                },
            )
