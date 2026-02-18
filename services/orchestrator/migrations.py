"""
Database Migration System — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Pure Python migration runner with SHA-256 checksums.
"""

import logging
import os
import hashlib
from datetime import datetime, timezone
from typing import List, Dict

logger = logging.getLogger("qwen.migrations")



# ============================================================================
#  MIGRATION DEFINITIONS
# ============================================================================

MIGRATIONS: List[Dict] = [
    {
        "version": "001",
        "name": "create_verification_jobs",
        "up": """
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
            CREATE INDEX IF NOT EXISTS idx_jobs_status ON verification_jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_industry ON verification_jobs(industry);
            CREATE INDEX IF NOT EXISTS idx_jobs_created ON verification_jobs(created_at DESC);
        """,
        "down": "DROP TABLE IF EXISTS verification_jobs;",
    },
    {
        "version": "002",
        "name": "create_audit_events",
        "up": """
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT,
                status TEXT,
                details JSONB,
                previous_hash TEXT,
                integrity_hash TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor);
            CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action);
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp DESC);
        """,
        "down": "DROP TABLE IF EXISTS audit_events;",
    },
    {
        "version": "003",
        "name": "create_model_deployments",
        "up": """
            CREATE TABLE IF NOT EXISTS model_deployments (
                id SERIAL PRIMARY KEY,
                model_name TEXT NOT NULL,
                model_version TEXT NOT NULL,
                sha256_hash TEXT,
                license TEXT NOT NULL DEFAULT 'Apache-2.0',
                deployed_at TIMESTAMPTZ DEFAULT NOW(),
                retired_at TIMESTAMPTZ,
                parameters TEXT,
                quantization TEXT DEFAULT 'none',
                is_active BOOLEAN DEFAULT TRUE
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_active_model
                ON model_deployments(is_active) WHERE is_active = TRUE;
        """,
        "down": "DROP TABLE IF EXISTS model_deployments;",
    },
    {
        "version": "004",
        "name": "create_plugin_registry",
        "up": """
            CREATE TABLE IF NOT EXISTS plugin_registry (
                name TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                description TEXT,
                license TEXT NOT NULL,
                author TEXT,
                enabled BOOLEAN DEFAULT TRUE,
                registered_at TIMESTAMPTZ DEFAULT NOW()
            );
        """,
        "down": "DROP TABLE IF EXISTS plugin_registry;",
    },
    {
        "version": "005",
        "name": "create_migration_history",
        "up": """
            CREATE TABLE IF NOT EXISTS _migration_history (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMPTZ DEFAULT NOW(),
                checksum TEXT NOT NULL
            );
        """,
        "down": "DROP TABLE IF EXISTS _migration_history;",
    },
    {
        "version": "006",
        "name": "add_job_metadata_columns",
        "up": """
            ALTER TABLE verification_jobs ADD COLUMN IF NOT EXISTS tenant_id TEXT DEFAULT 'default';
            ALTER TABLE verification_jobs ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '{}';
            ALTER TABLE verification_jobs ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 5;
            ALTER TABLE verification_jobs ADD COLUMN IF NOT EXISTS webhook_url TEXT;
        """,
        "down": """
            ALTER TABLE verification_jobs DROP COLUMN IF EXISTS tenant_id;
            ALTER TABLE verification_jobs DROP COLUMN IF EXISTS tags;
            ALTER TABLE verification_jobs DROP COLUMN IF EXISTS priority;
            ALTER TABLE verification_jobs DROP COLUMN IF EXISTS webhook_url;
        """,
    },
    {
        "version": "007",
        "name": "add_tenant_index",
        "up": """
            CREATE INDEX IF NOT EXISTS idx_jobs_tenant ON verification_jobs(tenant_id);
            CREATE INDEX IF NOT EXISTS idx_jobs_priority ON verification_jobs(priority);
            CREATE INDEX IF NOT EXISTS idx_audit_target ON audit_events(target);
        """,
        "down": """
            DROP INDEX IF EXISTS idx_jobs_tenant;
            DROP INDEX IF EXISTS idx_jobs_priority;
            DROP INDEX IF EXISTS idx_audit_target;
        """,
    },
]


# ============================================================================
#  MIGRATION RUNNER
# ============================================================================

class MigrationRunner:
    """
    Runs database migrations in order.
    Tracks applied migrations in _migration_history table.
    """

    def __init__(self, db_url: str = ""):
        self.db_url = db_url or os.getenv("POSTGRES_URL", "")

    def _checksum(self, sql: str) -> str:
        return hashlib.sha256(sql.strip().encode()).hexdigest()[:16]

    async def get_applied(self) -> List[str]:
        """Get list of already-applied migration versions."""
        if not self.db_url:
            return []
        try:
            import psycopg
            async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                async with conn.cursor() as cur:
                    # Create migration history table if not exists
                    await cur.execute(MIGRATIONS[-1]["up"])
                    await conn.commit()
                    await cur.execute("SELECT version FROM _migration_history ORDER BY version")
                    rows = await cur.fetchall()
                    return [r[0] for r in rows]
        except Exception:
            return []

    async def migrate(self) -> List[str]:
        """Run all pending migrations. Returns list of applied migration names."""
        if not self.db_url:
            logger.warning("No POSTGRES_URL — skipping migrations")
            return []

        applied = await self.get_applied()
        newly_applied = []

        try:
            import psycopg
            async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                for migration in MIGRATIONS:
                    if migration["version"] in applied:
                        continue
                    async with conn.cursor() as cur:
                        await cur.execute(migration["up"])
                        await cur.execute(
                            "INSERT INTO _migration_history (version, name, checksum) VALUES (%s, %s, %s) "
                            "ON CONFLICT (version) DO NOTHING",
                            (migration["version"], migration["name"], self._checksum(migration["up"]))
                        )
                    await conn.commit()
                    newly_applied.append(migration["name"])
                    logger.info(f"Migration applied: {migration['version']} — {migration['name']}")
        except Exception as e:
            logger.error(f"Migration error: {e}")

        return newly_applied

    async def rollback(self, version: str) -> bool:
        """Rollback a specific migration."""
        if not self.db_url:
            return False

        migration = next((m for m in MIGRATIONS if m["version"] == version), None)
        if not migration:
            return False

        try:
            import psycopg
            async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(migration["down"])
                    await cur.execute("DELETE FROM _migration_history WHERE version = %s", (version,))
                await conn.commit()
                logger.info(f"Migration rolled back: {version} — {migration['name']}")
                return True
        except Exception as e:
            logger.error(f"Migration rollback error: {e}")
            return False


# Global runner
migration_runner = MigrationRunner()
