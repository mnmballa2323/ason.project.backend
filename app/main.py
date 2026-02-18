from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time

from app.core.config import ALLOWED_ORIGINS
from app.core.logging import logger
from app.core.errors import AsonBaseError, ason_exception_handler, generic_exception_handler
# Telemetry
from services.telemetry import setup_telemetry
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize Telemetry
setup_telemetry("ason-orchestrator")

# Middleware
from app.core.middleware import (
    request_id_middleware,
    security_headers,
    ip_allowlist_middleware,
    rate_limiter,
    usage_metering_middleware,
    data_sovereignty_guard
)
from fastapi.middleware.gzip import GZipMiddleware

# Services
from app.services.job_store import job_store
from app.services.sovereignty import data_sovereignty
from services.telemetry import setup_telemetry
from services.secret_rotation import secret_rotation

# Routers
from app.routers import verify, dashboard, system, webhooks

# ============================================================================
#  APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title="Ason Verification Orchestrator",
    description="Mission-Critical AI Verification — Liberty Center One. (Refactored v2.1)",
    version="2.1.0",
    docs_url=None,   # Disabled at root — served at /system/docs
    redoc_url=None,  # Disabled at root — served at /system/redoc
    openapi_url=None,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Jurisdiction", "X-Request-ID"],
    max_age=600,
)

# --- Register Middleware (Order Matters) ---
# 1. Request ID (Traceability)
app.middleware("http")(request_id_middleware)
# 2. Security Headers (Harden response)
app.middleware("http")(security_headers)
# 3. IP Allowlist (Firewall)
app.middleware("http")(ip_allowlist_middleware)
# 4. Rate Limiter (Governance)
app.middleware("http")(rate_limiter)
# 5. Usage Metering (Billing/Telemetry)
app.middleware("http")(usage_metering_middleware)
# 6. Data Sovereignty (Compliance)
app.middleware("http")(data_sovereignty_guard)


# --- Register Exception Handlers ---
app.add_exception_handler(AsonBaseError, ason_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)


# --- Include Routers ---
app.include_router(verify.router, prefix="/verify")
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(dashboard.router, prefix="/dashboard")
app.include_router(system.router) # /health, /system
app.include_router(webhooks.router) # /internal/alert


# --- Lifecycle Events ---

@app.on_event("startup")
async def startup_init():
    FastAPIInstrumentor.instrument_app(app)
    
    # Enable Gzip Compression (Minimum size: 1000 bytes)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    """Initialize persistent stores and run migrations on application startup."""
    logger.info("Startup: Initializing resources...")
    await job_store.initialize()
    await data_sovereignty.initialize()
    
    from app.services.usage import usage_service
    await usage_service.initialize()
    
    # Run database migrations (optional if module exists)
    try:
        from migrations import migration_runner
        applied = await migration_runner.migrate()
        if applied:
            logger.info(f"Applied {len(applied)} database migrations.")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Migration skipped: {e}")

    logger.info("Ason Verification Orchestrator started (Liberty Center One)")


@app.on_event("shutdown")
async def shutdown_drain():
    """Graceful shutdown."""
    logger.info("Shutdown initiated...")
    # Add drain logic here if needed beyond standard ASGI handling
    logger.info("Shutdown complete.")
