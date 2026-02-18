"""
Centralized Error Handling — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Custom exception hierarchy + standardized error responses.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


# ============================================================================
#  CUSTOM EXCEPTION HIERARCHY
# ============================================================================

class AsonBaseError(Exception):
    """Base exception for all Ason platform errors."""
    status_code: int = 500
    error_code: str = "ASON_INTERNAL_ERROR"
    message: str = "An internal error occurred"

    def __init__(self, message: str = None, details: Any = None):
        self.message = message or self.__class__.message
        self.details = details
        super().__init__(self.message)


class ValidationError(AsonBaseError):
    status_code = 422
    error_code = "ASON_VALIDATION_ERROR"
    message = "Input validation failed"


class ClaimTooLargeError(ValidationError):
    error_code = "ASON_CLAIM_TOO_LARGE"
    message = "Claim exceeds maximum character limit"


class TooManyClaimsError(ValidationError):
    error_code = "ASON_TOO_MANY_CLAIMS"
    message = "Request exceeds maximum number of claims"


class InvalidIndustryError(ValidationError):
    error_code = "ASON_INVALID_INDUSTRY"
    message = "Industry not in allowed list"


class AuthenticationError(AsonBaseError):
    status_code = 401
    error_code = "ASON_AUTH_ERROR"
    message = "Authentication required"


class AuthorizationError(AsonBaseError):
    status_code = 403
    error_code = "ASON_FORBIDDEN"
    message = "Insufficient permissions"


class RateLimitError(AsonBaseError):
    status_code = 429
    error_code = "ASON_RATE_LIMIT"
    message = "Rate limit exceeded"


class JobNotFoundError(AsonBaseError):
    status_code = 404
    error_code = "ASON_JOB_NOT_FOUND"
    message = "Verification job not found"


class InferenceError(AsonBaseError):
    status_code = 502
    error_code = "ASON_INFERENCE_ERROR"
    message = "Inference service unavailable"


class PipelineError(AsonBaseError):
    status_code = 500
    error_code = "ASON_PIPELINE_ERROR"
    message = "Verification pipeline error"


class AuditChainError(AsonBaseError):
    status_code = 500
    error_code = "ASON_AUDIT_CHAIN_BROKEN"
    message = "Audit chain integrity compromised"


class ConcurrentLimitError(AsonBaseError):
    status_code = 429
    error_code = "ASON_CONCURRENT_LIMIT"
    message = "Concurrent job limit exceeded for this tenant"


class IPBlockedError(AsonBaseError):
    status_code = 403
    error_code = "ASON_IP_BLOCKED"
    message = "Request origin not in IP allowlist"


class RBACViolationError(AsonBaseError):
    status_code = 403
    error_code = "ASON_RBAC_VIOLATION"
    message = "Insufficient role permissions for this action"


# ============================================================================
#  STANDARDIZED API RESPONSE ENVELOPE
# ============================================================================

class APIResponse:
    """
    Standardized response envelope.
    All API responses follow this format:

    Success:
    {
        "success": true,
        "data": { ... },
        "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
    }

    Error:
    {
        "success": false,
        "error": { "code": "ASON_...", "message": "...", "details": ... },
        "meta": { "request_id": "...", "timestamp": "...", "version": "2.0.0" }
    }
    """

    @staticmethod
    def success(data: Any, request_id: str = "", status_code: int = 200) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "success": True,
                "data": data,
                "meta": {
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "2.0.0",
                    "deployment": "Liberty Center One",
                },
            },
        )

    @staticmethod
    def error(
        error_code: str,
        message: str,
        status_code: int = 500,
        details: Any = None,
        request_id: str = "",
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": details,
                },
                "meta": {
                    "request_id": request_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "2.0.0",
                    "deployment": "Liberty Center One",
                },
            },
        )


# ============================================================================
#  EXCEPTION HANDLERS (Register with FastAPI app)
# ============================================================================

async def ason_exception_handler(request: Request, exc: AsonBaseError) -> JSONResponse:
    """Handle all Ason custom exceptions."""
    request_id = getattr(request.state, "request_id", "unknown")
    return APIResponse.error(
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        request_id=request_id,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unhandled exceptions — never leak stack traces."""
    request_id = getattr(request.state, "request_id", "unknown")
    return APIResponse.error(
        error_code="ASON_INTERNAL_ERROR",
        message="An unexpected error occurred. This has been logged.",
        status_code=500,
        request_id=request_id,
    )


def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app."""
    app.add_exception_handler(AsonBaseError, ason_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
