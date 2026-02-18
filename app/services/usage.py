import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List
from collections import defaultdict
import os

logger = logging.getLogger("qwen.orchestrator")

# In-memory buffer for high-throughput metrics
# We flush this to DB periodically or on shutdown
_buffer: List[dict] = []
BUFFER_SIZE_LIMIT = 100

class UsageMetricsService:
    """
    Manages persistence of usage data to PostgreSQL.
    """
    DDL = """
    CREATE TABLE IF NOT EXISTS usage_metrics (
        metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        method TEXT NOT NULL,
        status_code INTEGER,
        latency_ms DOUBLE PRECISION,
        timestamp TIMESTAMPTZ DEFAULT NOW(),
        request_id TEXT
    );
    """

    def __init__(self):
        self.db_url = os.getenv("POSTGRES_URL", "")
        self._db_available = False

    async def initialize(self):
        if not self.db_url:
            return
        
        try:
            import psycopg
            async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(self.DDL)
                await conn.commit()
            self._db_available = True
            logger.info("Usage Metrics: Connected to PostgreSQL.")
        except Exception as e:
            logger.error(f"Usage Metrics DB Init Failed: {e}")

    async def record_request(self, tenant: str, method: str, path: str, status: int, latency: float, request_id: str):
        """Buffer a request metric."""
        metric = {
            "tenant_id": tenant,
            "endpoint": path,
            "method": method,
            "status_code": status,
            "latency_ms": latency,
            "timestamp": datetime.now(timezone.utc),
            "request_id": request_id
        }
        _buffer.append(metric)
        
        if len(_buffer) >= BUFFER_SIZE_LIMIT:
            await self.flush()

    async def flush(self):
        """Flush buffer to DB."""
        if not _buffer or not self._db_available:
            return

        batch = list(_buffer) # Copy
        _buffer.clear()
        
        try:
            import psycopg
            async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                async with conn.cursor() as cur:
                    # Batch insert
                    await cur.executemany(
                        """
                        INSERT INTO usage_metrics (tenant_id, endpoint, method, status_code, latency_ms, timestamp, request_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        [(m["tenant_id"], m["endpoint"], m["method"], m["status_code"], m["latency_ms"], m["timestamp"], m["request_id"]) for m in batch]
                    )
                await conn.commit()
        except Exception as e:
            logger.error(f"Usage Metrics Flush Failed: {e}")
            # In a real system, we might retry or drop. For now, we drop to avoid memory leak if DB is down.

usage_service = UsageMetricsService()
