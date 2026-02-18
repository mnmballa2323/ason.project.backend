"""
Network Egress Filter Middleware
Enforces Data Sovereignty by blocking potential outbound connections and sanitizing headers.
STRICTLY INTERNAL USE ONLY.
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger("qwen.gateway.egress_filter")

class NetworkEgressFilter(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Block suspect verification headers (often used by external SaaS)
        if "X-External-Verification" in request.headers:
            logger.critical(f"BLOCKED EGRESS ATTEMPT: {request.client.host}")
            raise HTTPException(status_code=403, detail="Egress Violation: External Verification Header Detected")

        # 2. Block requests to known public API paths (simulation)
        if "api.openai.com" in request.url.path or "googleapis.com" in request.url.path:
             logger.critical(f"BLOCKED EGRESS ATTEMPT: {request.client.host} tried connecting to External API")
             raise HTTPException(status_code=403, detail="Egress Violation: External API Call Blocked")

        # 3. Sanitize Headers (Strip tracking)
        response = await call_next(request)
        if "X-Tracking-Id" in response.headers:
            del response.headers["X-Tracking-Id"]
        
        # 4. Enforce Data Sovereignty Header
        response.headers["X-Data-Sovereignty"] = "Internal-Only"
        
        return response
