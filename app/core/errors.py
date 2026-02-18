from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("qwen.orchestrator")

class AsonBaseError(Exception):
    """Base class for all application errors."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: dict = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


async def ason_exception_handler(request: Request, exc: AsonBaseError):
    """Handle custom Ason exceptions."""
    logger.error(f"AsonError: {exc.code} - {exc.message}", extra={"details": exc.details})
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "details": exc.details,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please contact support.",
        },
    )
