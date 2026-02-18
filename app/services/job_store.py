import os
import logging
from typing import Dict, Optional, List
from datetime import datetime, timezone

# Assuming you might need psycopg here if not already installed, 
# but we'll stick to the logic found in main.py
# If main.py used asyncpg or psycopg, we replicate that.
# main.py used 'import psycopg' inside methods.

logger = logging.getLogger("qwen.orchestrator")

class PersistentJobStore:
    """
    PostgreSQL-backed job store. Falls back to in-memory dict if DB unavailable.
    Table: verification_jobs (auto-created on startup).
    """
    DDL = """
    CREATE TABLE IF NOT EXISTS verification_jobs (
        job_id TEXT PRIMARY KEY,
        status TEXT NOT NULL DEFAULT 'queued',
        industry TEXT,
        total_claims INTEGER DEFAULT 0,
        progress INTEGER DEFAULT 0,
        result TEXT,
        error TEXT,
        model_version TEXT,
        started_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """

    def __init__(self):
        self.db_url = os.getenv("POSTGRES_URL", "")
        self._memory: Dict[str, dict] = {}  # Fallback
        self._db_available = False

    async def initialize(self):
        """Create table if PostgreSQL is available."""
        if not self.db_url:
            logger.warning("JobStore: POSTGRES_URL not set. Using in-memory storage (data lost on restart).")
            return

        try:
            import psycopg
            async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(self.DDL)
                await conn.commit()
            self._db_available = True
            logger.info("JobStore: Connected to PostgreSQL.")
        except Exception as e:
            logger.error(f"JobStore: DB Connection failed: {e}. Falling back to in-memory.")

    async def create(self, job_id: str, industry: str, total_claims: int, model_version: str = "ason-72b"):
        job = {
            "job_id": job_id,
            "status": "queued",
            "industry": industry,
            "total_claims": total_claims,
            "progress": 0,
            "result": None,
            "error": None,
            "model_version": model_version,
            "started_at": None,
            "completed_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        if self._db_available:
            try:
                import psycopg
                async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "INSERT INTO verification_jobs (job_id, industry, total_claims, model_version) VALUES (%s, %s, %s, %s)",
                            (job_id, industry, total_claims, model_version)
                        )
                    await conn.commit()
            except Exception as e:
                logger.error(f"JobStore: Failed to persist create: {e}")
                self._memory[job_id] = job # Fallback
        else:
            self._memory[job_id] = job

    async def update(self, job_id: str, **kwargs):
        # Update memory first if used
        if job_id in self._memory:
            self._memory[job_id].update(kwargs)

        if self._db_available:
            try:
                import psycopg
                set_clauses = []
                values = []
                for k, v in kwargs.items():
                    set_clauses.append(f"{k} = %s")
                    values.append(v)
                values.append(job_id)
                
                query = f"UPDATE verification_jobs SET {', '.join(set_clauses)} WHERE job_id = %s"
                
                async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(query, values)
                    await conn.commit()
            except Exception as e:
                logger.error(f"JobStore: Failed to persist update: {e}")

    async def get(self, job_id: str) -> Optional[dict]:
        if self._db_available:
            try:
                import psycopg
                async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                    async with conn.cursor() as cur: # Use DictCursor if available, else manual
                        from psycopg.rows import dict_row
                        cur.row_factory = dict_row
                        await cur.execute("SELECT * FROM verification_jobs WHERE job_id = %s", (job_id,))
                        return await cur.fetchone()
            except Exception as e:
                logger.error(f"JobStore: Failed to fetch: {e}")
                return self._memory.get(job_id)
        
        return self._memory.get(job_id)

    async def list_all(self) -> List[dict]:
        if self._db_available:
             try:
                import psycopg
                from psycopg.rows import dict_row
                async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                    async with conn.cursor(row_factory=dict_row) as cur:
                        await cur.execute("SELECT * FROM verification_jobs ORDER BY created_at DESC LIMIT 100")
                        return await cur.fetchall()
             except Exception:
                 return list(self._memory.values())
        return list(self._memory.values())

job_store = PersistentJobStore()
