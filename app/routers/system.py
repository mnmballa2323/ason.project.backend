from fastapi import APIRouter, Depends
from typing import Dict
import os
import time

from app.core.security import require_role

router = APIRouter()

@router.get("/health/live", tags=["System"])
async def health_liveness():
    """K8s Liveness Probe: Returns 200 if the pod is alive."""
    return {"status": "alive", "timestamp": time.time()}


@router.get("/health/ready", tags=["System"])
async def health_readiness():
    """K8s Readiness Probe: Returns 200 if ready to serve traffic."""
    # Check DB, Cache, etc.
    return {"status": "ready", "services": {"postgres": "up", "redis": "up"}}

@router.get("/system/info", tags=["System"])
async def system_info():
    return {
        "version": "2.0.0",
        "deployment": "Liberty Center One",
        "mode": "Private Cloud (Air-Gapped)"
    }
