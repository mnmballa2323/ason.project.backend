import uuid
import time
import hashlib
import ipaddress
from datetime import datetime, timezone
from typing import Dict, Any, List
from collections import defaultdict

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

from app.core.config import (
    HMAC_SECRET, IP_ALLOWLIST_CIDRS, RATE_LIMIT_MAX, RATE_LIMIT_WINDOW, SERVER_JURISDICTION_STR
)
from data_sovereignty import data_sovereignty, Jurisdiction, DataCategory

logger = logging.getLogger("qwen.orchestrator")

# --- Rate Limiting Store ---
rate_limit_store: Dict[str, List[float]] = defaultdict(list)

# --- Usage Metering Store ---
_usage_store: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "total_requests": 0,
    "total_jobs": 0,
    "endpoints": defaultdict(int),
    "first_seen": None,
    "last_seen": None,
})
_sla_tracker: Dict[str, list] = {"latencies_ms": [], "successes": 0, "failures": 0, "start_time": time.time()}

# --- IP Allowlist Object ---
IP_ALLOWLIST = [
    ipaddress.ip_network(cidr, strict=False) for cidr in IP_ALLOWLIST_CIDRS
]

# --- Server Jurisdiction ---
SERVER_JURISDICTION = Jurisdiction(SERVER_JURISDICTION_STR)


async def request_id_middleware(request: Request, call_next):
    """Attach a unique X-Request-ID to every request for distributed tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


async def security_headers(request: Request, call_next):
    """Government-grade security headers on every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self' wss://qwen.libertycenter.one"
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
    # Wave 15: HMAC response signing
    response.headers["X-Response-Timestamp"] = datetime.now(timezone.utc).isoformat()
    sig_payload = f"{request.url.path}:{response.status_code}:{response.headers.get('X-Request-ID', '')}"
    response.headers["X-Response-Signature"] = hashlib.sha256(
        f"{HMAC_SECRET}:{sig_payload}".encode()
    ).hexdigest()[:32]
    return response


async def ip_allowlist_middleware(request: Request, call_next):
    """Reject requests from non-allowlisted IPs."""
    if IP_ALLOWLIST:
        client_ip = request.client.host if request.client else None
        if client_ip:
            try:
                addr = ipaddress.ip_address(client_ip)
                if not any(addr in net for net in IP_ALLOWLIST):
                    logger.warning(f"IP blocked by allowlist: {client_ip}")
                    return JSONResponse(
                        status_code=403,
                        content={"detail": f"IP {client_ip} not in allowlist. Contact your administrator."},
                    )
            except ValueError:
                pass
    return await call_next(request)


async def rate_limiter(request: Request, call_next):
    """Sliding-window rate limiter (per-IP)."""
    rate_key = request.client.host if request.client else "unknown"
    now = time.time()
    rate_limit_store[rate_key] = [t for t in rate_limit_store[rate_key] if now - t < RATE_LIMIT_WINDOW]

    if len(rate_limit_store[rate_key]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail=f"Rate limit exceeded. Max {RATE_LIMIT_MAX} req/{RATE_LIMIT_WINDOW}s.")

    rate_limit_store[rate_key].append(now)
    response = await call_next(request)
    response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT_MAX - len(rate_limit_store[rate_key]))
    return response


async def usage_metering_middleware(request: Request, call_next):
    """Track per-tenant API usage for billing and analytics."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    tenant = "anonymous"
    try:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            tenant = "jwt_tenant"
        elif "localhost" in str(request.base_url):
            tenant = "dev_tenant"
    except Exception:
        pass

    # Persist via service
    from app.services.usage import usage_service
    # Fire and forget (in background would be better, but direct await is safe if async)
    # To truly be non-blocking, we'd use BackgroundTasks, but middleware can't easily inject that.
    # The usage_service buffers in memory, so this await is fast (just appending to list).
    await usage_service.record_request(
        tenant=tenant,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        latency=duration_ms,
        request_id=getattr(request.state, "request_id", None)
    )

    return response


async def data_sovereignty_guard(request: Request, call_next):
    """
    middleware: Hard enforcement of Data Sovereignty.
    Intercepts every request to validate Source vs. Target jurisdiction.
    """
    client_loc_str = request.headers.get("X-Jurisdiction", "GLOBAL")
    try:
        client_jurisdiction = Jurisdiction(client_loc_str)
    except ValueError:
        client_jurisdiction = Jurisdiction.GLOBAL

    path = request.url.path
    category = DataCategory.METADATA
    if "/onboard" in path:
        category = DataCategory.PII
    elif "/verify" in path:
        category = DataCategory.VERIFICATION
    elif "/dashboard/security" in path:
        category = DataCategory.SENSITIVE_PII
    elif "/admin" in path:
        category = DataCategory.TOP_SECRET if "secret" in path else DataCategory.EMPLOYEE

    # Ingress (Client -> Server)
    if request.method in ["POST", "PUT", "PATCH"]:
        result = data_sovereignty.validate_transfer(
            source_jurisdiction=client_jurisdiction,
            target_jurisdiction=SERVER_JURISDICTION,
            data_category=category
        )
        if not result["allowed"]:
            logger.warning(f"Data Sovereignty Block (Ingress): {client_jurisdiction} -> {SERVER_JURISDICTION}")
            return JSONResponse(
                status_code=451,
                content={
                    "error": "Data Sovereignty Violation",
                    "detail": result,
                    "message": f"Transfer from {client_jurisdiction.value} to {SERVER_JURISDICTION.value} prohibited for {category.value}."
                }
            )

    # Egress (Server -> Client)
    if request.method in ["GET"]:
        result = data_sovereignty.validate_transfer(
            source_jurisdiction=SERVER_JURISDICTION,
            target_jurisdiction=client_jurisdiction,
            data_category=category
        )
        if not result["allowed"]:
            logger.warning(f"Data Sovereignty Block (Egress): {SERVER_JURISDICTION} -> {client_jurisdiction}")
            return JSONResponse(
                status_code=451,
                content={
                    "error": "Data Sovereignty Violation",
                    "detail": result,
                    "message": f"Export from {SERVER_JURISDICTION.value} to {client_jurisdiction.value} prohibited for {category.value}."
                }
            )

    return await call_next(request)
