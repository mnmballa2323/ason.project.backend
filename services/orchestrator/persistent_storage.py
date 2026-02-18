"""
Persistent Storage Layer — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

SQLite backend, migration engine, query builder — stdlib only.
"""

import hashlib, json, logging, os, sqlite3, threading, time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("qwen.storage")

DB_DIR = Path(os.environ.get("ASON_DATA_DIR", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".ason_data")))


# ============================================================================
#  SQLITE BACKEND
# ============================================================================

class StorageBackend:
    """Thread-safe SQLite backend with WAL mode and connection pooling."""

    def __init__(self, db_name: str = "ason_security.db"):
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self._db_path = str(DB_DIR / db_name)
        self._local = threading.local()
        self._lock = threading.Lock()

        # Initialize with WAL mode for concurrent reads
        conn = self._get_conn()
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.commit()

        self._run_migrations()
        logger.info("Storage backend initialized: %s", self._db_path)

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                self._db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._get_conn().execute(sql, params)

    def executemany(self, sql: str, params_list: List[tuple]) -> None:
        self._get_conn().executemany(sql, params_list)

    def commit(self):
        self._get_conn().commit()

    def fetchall(self, sql: str, params: tuple = ()) -> List[Dict]:
        cursor = self._get_conn().execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]

    def fetchone(self, sql: str, params: tuple = ()) -> Optional[Dict]:
        cursor = self._get_conn().execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def _run_migrations(self):
        """Run all pending migrations."""
        self.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """)
        self.commit()

        applied = {r["version"] for r in self.fetchall(
            "SELECT version FROM _migrations")}

        for migration in MIGRATIONS:
            if migration.version not in applied:
                logger.info("Applying migration v%d: %s",
                           migration.version, migration.name)
                for stmt in migration.statements:
                    self.execute(stmt)
                checksum = hashlib.sha256(
                    ";".join(migration.statements).encode()).hexdigest()[:16]
                self.execute(
                    "INSERT INTO _migrations (version, name, checksum, applied_at) "
                    "VALUES (?, ?, ?, ?)",
                    (migration.version, migration.name, checksum,
                     datetime.now(timezone.utc).isoformat()))
                self.commit()
                logger.info("Migration v%d applied", migration.version)

    def get_stats(self) -> Dict:
        page_count = self.fetchone("PRAGMA page_count")
        page_size = self.fetchone("PRAGMA page_size")
        pages = page_count["page_count"] if page_count else 0
        size = page_size["page_size"] if page_size else 4096
        migrations = self.fetchall("SELECT version, name, applied_at FROM _migrations ORDER BY version")
        return {
            "db_path": self._db_path,
            "db_size_bytes": pages * size,
            "db_size_mb": round(pages * size / 1048576, 2),
            "wal_mode": True,
            "migrations_applied": len(migrations),
            "latest_migration": migrations[-1]["name"] if migrations else None,
        }


# ============================================================================
#  MIGRATION ENGINE
# ============================================================================

class Migration:
    def __init__(self, version: int, name: str, statements: List[str]):
        self.version = version
        self.name = name
        self.statements = statements


MIGRATIONS = [
    Migration(1, "create_events_table", [
        """CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            event_type TEXT NOT NULL,
            source TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'info',
            message TEXT NOT NULL,
            data TEXT,
            tags TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            INDEX_source TEXT GENERATED ALWAYS AS (source) VIRTUAL
        )""".replace("INDEX_source TEXT GENERATED ALWAYS AS (source) VIRTUAL", ""),
        "CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)",
        "CREATE INDEX IF NOT EXISTS idx_events_source ON events(source)",
        "CREATE INDEX IF NOT EXISTS idx_events_severity ON events(severity)",
        "CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at)",
    ]),
    Migration(2, "create_audit_log", [
        """CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            target TEXT,
            details TEXT,
            ip_address TEXT,
            session_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor)",
        "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)",
        "CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at)",
    ]),
    Migration(3, "create_secrets_table", [
        """CREATE TABLE IF NOT EXISTS secrets (
            key TEXT PRIMARY KEY,
            value_encrypted TEXT NOT NULL,
            metadata TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT
        )""",
    ]),
    Migration(4, "create_lineage_table", [
        """CREATE TABLE IF NOT EXISTS data_lineage (
            id TEXT PRIMARY KEY,
            data_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            actor TEXT NOT NULL,
            action TEXT NOT NULL,
            input_hash TEXT,
            output_hash TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_lineage_data ON data_lineage(data_id)",
        "CREATE INDEX IF NOT EXISTS idx_lineage_stage ON data_lineage(stage)",
    ]),
    Migration(5, "create_incidents_table", [
        """CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'open',
            assignee TEXT,
            description TEXT,
            timeline TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            resolved_at TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status)",
        "CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents(severity)",
    ]),
    Migration(6, "create_metrics_table", [
        """CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            value REAL NOT NULL,
            labels TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
        "CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name)",
        "CREATE INDEX IF NOT EXISTS idx_metrics_created ON metrics(created_at)",
    ]),
    Migration(7, "create_policies_table", [
        """CREATE TABLE IF NOT EXISTS policies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            rules TEXT NOT NULL,
            enforcement TEXT NOT NULL DEFAULT 'enforce',
            priority INTEGER NOT NULL DEFAULT 5,
            enabled INTEGER NOT NULL DEFAULT 1,
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
    ]),
    Migration(8, "create_config_table", [
        """CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            description TEXT,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""",
    ]),
]


# ============================================================================
#  QUERY ENGINE
# ============================================================================

class QueryOp(str, Enum):
    EQ = "="
    NE = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    LIKE = "LIKE"
    IN = "IN"


class QueryBuilder:
    """Structured, injection-safe query builder."""

    def __init__(self, table: str):
        self._table = table
        self._selects: List[str] = ["*"]
        self._wheres: List[Tuple[str, str, Any]] = []
        self._orders: List[Tuple[str, str]] = []
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._group_by: Optional[str] = None

    def select(self, *columns: str) -> "QueryBuilder":
        self._selects = list(columns)
        return self

    def where(self, column: str, op: str, value: Any) -> "QueryBuilder":
        self._wheres.append((column, op, value))
        return self

    def order_by(self, column: str, direction: str = "ASC") -> "QueryBuilder":
        self._orders.append((column, direction.upper()))
        return self

    def limit(self, n: int) -> "QueryBuilder":
        self._limit = n
        return self

    def offset(self, n: int) -> "QueryBuilder":
        self._offset = n
        return self

    def group_by(self, column: str) -> "QueryBuilder":
        self._group_by = column
        return self

    def build(self) -> Tuple[str, tuple]:
        """Build parameterized SQL query."""
        parts = [f"SELECT {', '.join(self._selects)} FROM {self._table}"]
        params = []

        if self._wheres:
            clauses = []
            for col, op, val in self._wheres:
                if op.upper() == "IN" and isinstance(val, (list, tuple)):
                    placeholders = ", ".join("?" * len(val))
                    clauses.append(f"{col} IN ({placeholders})")
                    params.extend(val)
                else:
                    clauses.append(f"{col} {op} ?")
                    params.append(val)
            parts.append("WHERE " + " AND ".join(clauses))

        if self._group_by:
            parts.append(f"GROUP BY {self._group_by}")

        if self._orders:
            order_parts = [f"{col} {d}" for col, d in self._orders]
            parts.append("ORDER BY " + ", ".join(order_parts))

        if self._limit is not None:
            parts.append(f"LIMIT {self._limit}")

        if self._offset is not None:
            parts.append(f"OFFSET {self._offset}")

        return " ".join(parts), tuple(params)

    def count(self) -> Tuple[str, tuple]:
        """Build a COUNT query."""
        self._selects = ["COUNT(*) as count"]
        return self.build()


# ============================================================================
#  CONVENIENCE API
# ============================================================================

class EventStore:
    """High-level API for event persistence."""

    def __init__(self, backend: StorageBackend):
        self._db = backend

    def insert(self, event_id: str, event_type: str, source: str,
              severity: str, message: str, data: Dict = None,
              tags: List[str] = None) -> str:
        self._db.execute(
            "INSERT INTO events (id, event_type, source, severity, message, data, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (event_id, event_type, source, severity, message,
             json.dumps(data) if data else None,
             json.dumps(tags) if tags else None))
        self._db.commit()
        return event_id

    def query(self, event_type: str = None, source: str = None,
             severity: str = None, limit: int = 100) -> List[Dict]:
        qb = QueryBuilder("events")
        if event_type:
            qb.where("event_type", "=", event_type)
        if source:
            qb.where("source", "=", source)
        if severity:
            qb.where("severity", "=", severity)
        qb.order_by("created_at", "DESC").limit(limit)
        sql, params = qb.build()
        return self._db.fetchall(sql, params)

    def count(self, event_type: str = None) -> int:
        qb = QueryBuilder("events")
        if event_type:
            qb.where("event_type", "=", event_type)
        sql, params = qb.count()
        result = self._db.fetchone(sql, params)
        return result["count"] if result else 0


class AuditStore:
    """High-level API for audit log persistence."""

    def __init__(self, backend: StorageBackend):
        self._db = backend

    def log(self, action: str, actor: str, target: str = None,
           details: Dict = None, ip_address: str = None,
           session_id: str = None) -> int:
        cursor = self._db.execute(
            "INSERT INTO audit_log (action, actor, target, details, ip_address, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (action, actor, target,
             json.dumps(details) if details else None,
             ip_address, session_id))
        self._db.commit()
        return cursor.lastrowid

    def query(self, actor: str = None, action: str = None,
             limit: int = 100) -> List[Dict]:
        qb = QueryBuilder("audit_log")
        if actor:
            qb.where("actor", "=", actor)
        if action:
            qb.where("action", "=", action)
        qb.order_by("created_at", "DESC").limit(limit)
        sql, params = qb.build()
        return self._db.fetchall(sql, params)


class MetricsStore:
    """High-level API for metrics persistence."""

    def __init__(self, backend: StorageBackend):
        self._db = backend

    def record(self, name: str, value: float, labels: Dict = None):
        self._db.execute(
            "INSERT INTO metrics (name, value, labels) VALUES (?, ?, ?)",
            (name, value, json.dumps(labels) if labels else None))
        self._db.commit()

    def query(self, name: str, limit: int = 100) -> List[Dict]:
        return self._db.fetchall(
            "SELECT * FROM metrics WHERE name = ? ORDER BY created_at DESC LIMIT ?",
            (name, limit))

    def aggregate(self, name: str, agg: str = "AVG") -> Optional[float]:
        agg = agg.upper()
        if agg not in ("AVG", "SUM", "MIN", "MAX", "COUNT"):
            return None
        result = self._db.fetchone(
            f"SELECT {agg}(value) as result FROM metrics WHERE name = ?",
            (name,))
        return result["result"] if result else None


# Lazy singleton
_backend_instance = None
_backend_lock = threading.Lock()


def get_storage() -> StorageBackend:
    global _backend_instance
    if _backend_instance is None:
        with _backend_lock:
            if _backend_instance is None:
                _backend_instance = StorageBackend()
    return _backend_instance


def get_event_store() -> EventStore:
    return EventStore(get_storage())


def get_audit_store() -> AuditStore:
    return AuditStore(get_storage())


def get_metrics_store() -> MetricsStore:
    return MetricsStore(get_storage())
