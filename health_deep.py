"""
Deep Health Check Aggregator — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Probes every component and returns per-component health detail.
"""

import asyncio
import logging
import os
import platform
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("qwen.health")


# ============================================================================
#  COMPONENT HEALTH STATUS
# ============================================================================

class ComponentStatus:
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """Individual component health check result."""

    def __init__(
        self, component: str, status: str,
        latency_ms: float = 0, message: str = "",
        details: Dict = None,
    ):
        self.component = component
        self.status = status
        self.latency_ms = latency_ms
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "status": self.status,
            "latency_ms": round(self.latency_ms, 2),
            "message": self.message,
            "details": self.details,
        }


# ============================================================================
#  HEALTH PROBES
# ============================================================================

async def probe_postgres() -> HealthCheck:
    """Probe PostgreSQL connectivity and performance."""
    start = time.time()
    try:
        db_url = os.getenv("POSTGRES_URL", "")
        if not db_url:
            return HealthCheck("postgres", ComponentStatus.UNKNOWN, message="No POSTGRES_URL configured")

        import psycopg
        async with await psycopg.AsyncConnection.connect(db_url, connect_timeout=5) as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                result = await cur.fetchone()

                # Get connection count
                await cur.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
                active_conns = (await cur.fetchone())[0]

                # Get database size
                await cur.execute("SELECT pg_database_size(current_database())")
                db_size_bytes = (await cur.fetchone())[0]

        latency = (time.time() - start) * 1000
        status = ComponentStatus.HEALTHY if latency < 100 else ComponentStatus.DEGRADED

        return HealthCheck("postgres", status, latency, "Connected", {
            "active_connections": active_conns,
            "database_size_mb": round(db_size_bytes / 1024 / 1024, 1),
        })
    except Exception as e:
        return HealthCheck("postgres", ComponentStatus.UNHEALTHY,
                           (time.time() - start) * 1000, str(e))


async def probe_milvus() -> HealthCheck:
    """Probe Milvus vector database."""
    start = time.time()
    try:
        milvus_host = os.getenv("MILVUS_HOST", "localhost")
        milvus_port = int(os.getenv("MILVUS_PORT", "19530"))

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(milvus_host, milvus_port), timeout=5
        )
        writer.close()
        await writer.wait_closed()

        latency = (time.time() - start) * 1000
        return HealthCheck("milvus", ComponentStatus.HEALTHY, latency, "TCP connected", {
            "host": milvus_host, "port": milvus_port,
        })
    except Exception as e:
        return HealthCheck("milvus", ComponentStatus.UNHEALTHY,
                           (time.time() - start) * 1000, str(e))


async def probe_inference() -> HealthCheck:
    """Probe inference engine health."""
    start = time.time()
    try:
        inference_url = os.getenv("INFERENCE_URL", "http://localhost:8000")
        health_url = f"{inference_url.rstrip('/')}/health"

        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(health_url)
            latency = (time.time() - start) * 1000

            if resp.status_code == 200:
                data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                return HealthCheck("inference", ComponentStatus.HEALTHY, latency, "Running", {
                    "model": data.get("model", "unknown"),
                    "gpu_memory_pct": data.get("gpu_memory_pct", None),
                })
            else:
                return HealthCheck("inference", ComponentStatus.DEGRADED, latency,
                                   f"HTTP {resp.status_code}")
    except Exception as e:
        return HealthCheck("inference", ComponentStatus.UNHEALTHY,
                           (time.time() - start) * 1000, str(e))


async def probe_disk() -> HealthCheck:
    """Check available disk space."""
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_pct = (free / total) * 100
        free_gb = free / (1024 ** 3)

        if free_pct < 5:
            status = ComponentStatus.UNHEALTHY
            msg = f"CRITICAL: Only {free_pct:.1f}% disk free"
        elif free_pct < 15:
            status = ComponentStatus.DEGRADED
            msg = f"Low disk: {free_pct:.1f}% free"
        else:
            status = ComponentStatus.HEALTHY
            msg = f"{free_gb:.1f} GB free ({free_pct:.1f}%)"

        return HealthCheck("disk", status, 0, msg, {
            "total_gb": round(total / (1024 ** 3), 1),
            "used_gb": round(used / (1024 ** 3), 1),
            "free_gb": round(free_gb, 1),
            "free_pct": round(free_pct, 1),
        })
    except Exception as e:
        return HealthCheck("disk", ComponentStatus.UNKNOWN, 0, str(e))


async def probe_memory() -> HealthCheck:
    """Check system memory usage."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        used_pct = mem.percent

        if used_pct > 95:
            status = ComponentStatus.UNHEALTHY
            msg = f"CRITICAL: {used_pct}% memory used"
        elif used_pct > 85:
            status = ComponentStatus.DEGRADED
            msg = f"High memory: {used_pct}% used"
        else:
            status = ComponentStatus.HEALTHY
            msg = f"{used_pct}% used"

        return HealthCheck("memory", status, 0, msg, {
            "total_gb": round(mem.total / (1024 ** 3), 1),
            "available_gb": round(mem.available / (1024 ** 3), 1),
            "used_pct": used_pct,
        })
    except ImportError:
        return HealthCheck("memory", ComponentStatus.UNKNOWN, 0, "psutil not available")
    except Exception as e:
        return HealthCheck("memory", ComponentStatus.UNKNOWN, 0, str(e))


# ============================================================================
#  HEALTH AGGREGATOR
# ============================================================================

class HealthAggregator:
    """
    Aggregates health checks from all components.
    Used by /health/deep endpoint and SLA dashboard.
    """

    def __init__(self):
        self._last_check: Optional[Dict] = None
        self._check_interval: float = 30.0  # Cache results for 30s
        self._last_check_time: float = 0

    async def check_all(self, use_cache: bool = True) -> Dict:
        """Run all health probes and aggregate results."""
        now = time.time()
        if use_cache and self._last_check and (now - self._last_check_time) < self._check_interval:
            return self._last_check

        # Run all probes concurrently
        results = await asyncio.gather(
            probe_postgres(),
            probe_milvus(),
            probe_inference(),
            probe_disk(),
            probe_memory(),
            return_exceptions=True,
        )

        components = []
        for r in results:
            if isinstance(r, HealthCheck):
                components.append(r.to_dict())
            elif isinstance(r, Exception):
                components.append(HealthCheck("unknown", ComponentStatus.UNHEALTHY, 0, str(r)).to_dict())

        # Determine overall status
        statuses = [c["status"] for c in components]
        if ComponentStatus.UNHEALTHY in statuses:
            overall = ComponentStatus.UNHEALTHY
        elif ComponentStatus.DEGRADED in statuses:
            overall = ComponentStatus.DEGRADED
        else:
            overall = ComponentStatus.HEALTHY

        result = {
            "status": overall,
            "version": os.getenv("ASON_VERSION", "2.0.0"),
            "uptime_seconds": round(now - _start_time, 1),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "components": components,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

        self._last_check = result
        self._last_check_time = now
        return result

    async def check_readiness(self) -> Dict:
        """Quick readiness check (just critical components)."""
        pg = await probe_postgres()
        inf = await probe_inference()

        ready = (pg.status != ComponentStatus.UNHEALTHY
                 and inf.status != ComponentStatus.UNHEALTHY)

        return {
            "status": "ready" if ready else "not_ready",
            "postgres": pg.status,
            "inference": inf.status,
        }

    async def check_liveness(self) -> Dict:
        """Liveness probe — just confirms the process is responding."""
        return {
            "status": "alive",
            "uptime_seconds": round(time.time() - _start_time, 1),
        }


_start_time = time.time()

# Global singleton
health_aggregator = HealthAggregator()
