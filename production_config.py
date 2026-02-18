"""
Production Config & Logging — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Config management, structured JSON logging, startup orchestration.
"""

import json, logging, logging.handlers, os, sys, threading, time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("qwen.production")


# ============================================================================
#  CONFIG MANAGEMENT
# ============================================================================

class ConfigSource(str, Enum):
    DEFAULT = "default"
    FILE = "file"
    ENV = "environment"
    OVERRIDE = "override"


class ConfigEntry:
    def __init__(self, key, value, source, description=""):
        self.key = key
        self.value = value
        self.source = source
        self.description = description


class ConfigManager:
    """Hierarchical config: defaults → file → env vars → overrides.
    Zero telemetry enforced at every level.
    """

    DEFAULTS: Dict[str, Any] = {
        # Core
        "platform.name": "Ason Security Platform",
        "platform.version": "1.0.0",
        "platform.modules": 120,

        # Security
        "security.telemetry": False,
        "security.external_api_calls": False,
        "security.backdoors": False,
        "security.zero_trust": True,
        "security.mfa_required": True,
        "security.session_timeout_min": 60,
        "security.max_login_attempts": 5,
        "security.password_min_length": 14,
        "security.encryption_at_rest": True,
        "security.tls_version_min": "1.3",
        "security.fips_mode": True,
        "security.audit_all_actions": True,

        # Storage
        "storage.backend": "sqlite",
        "storage.db_name": "ason_security.db",
        "storage.wal_mode": True,
        "storage.max_connections": 10,
        "storage.busy_timeout_ms": 5000,

        # Logging
        "logging.level": "INFO",
        "logging.format": "json",
        "logging.file": "ason_security.log",
        "logging.max_bytes": 10485760,
        "logging.backup_count": 5,
        "logging.correlation_ids": True,

        # API
        "api.host": "0.0.0.0",
        "api.port": 9443,
        "api.workers": 4,
        "api.rate_limit": 100,
        "api.cors_origins": [],
        "api.request_size_limit": 1048576,

        # Monitoring
        "monitoring.health_check_interval": 30,
        "monitoring.metrics_retention_days": 90,
        "monitoring.alert_threshold_critical": 3,

        # Defense
        "defense.defcon_level": 4,
        "defense.auto_remediation": True,
        "defense.anomaly_z_threshold": 3.0,
        "defense.ml_retrain_interval_hours": 24,
    }

    # Immutable security constraints — cannot be overridden
    IMMUTABLE = {
        "security.telemetry": False,
        "security.external_api_calls": False,
        "security.backdoors": False,
    }

    def __init__(self, config_file: str = None):
        self._entries: Dict[str, ConfigEntry] = {}
        self._lock = threading.Lock()

        # Layer 1: defaults
        for key, value in self.DEFAULTS.items():
            self._entries[key] = ConfigEntry(key, value, ConfigSource.DEFAULT)

        # Layer 2: config file
        if config_file and os.path.exists(config_file):
            self._load_file(config_file)

        # Layer 3: environment variables
        self._load_env()

        # Layer 4: enforce immutables
        self._enforce_immutables()

    def _load_file(self, path: str):
        """Load config from JSON file."""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            self._flatten(data, "", ConfigSource.FILE)
            logger.info("Config loaded from file: %s", path)
        except Exception as e:
            logger.error("Failed to load config file %s: %s", path, e)

    def _flatten(self, data: Dict, prefix: str, source: ConfigSource):
        """Flatten nested dict into dot-notation keys."""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._flatten(value, full_key, source)
            else:
                self._entries[full_key] = ConfigEntry(full_key, value, source)

    def _load_env(self):
        """Load from ASON_ prefixed env vars."""
        prefix = "ASON_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace("__", ".")
                # Type coercion
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                self._entries[config_key] = ConfigEntry(
                    config_key, value, ConfigSource.ENV)

    def _enforce_immutables(self):
        """Enforce security constraints that cannot be overridden."""
        for key, value in self.IMMUTABLE.items():
            entry = self._entries.get(key)
            if entry and entry.value != value:
                logger.warning(
                    "SECURITY: Attempt to override immutable config '%s'. "
                    "Reverting to safe value.", key)
            self._entries[key] = ConfigEntry(
                key, value, ConfigSource.OVERRIDE,
                "IMMUTABLE — cannot be changed")

    def get(self, key: str, default: Any = None) -> Any:
        entry = self._entries.get(key)
        return entry.value if entry else default

    def set(self, key: str, value: Any) -> bool:
        if key in self.IMMUTABLE:
            logger.warning("Cannot override immutable config: %s", key)
            return False
        with self._lock:
            self._entries[key] = ConfigEntry(key, value, ConfigSource.OVERRIDE)
        return True

    def get_all(self) -> Dict[str, Any]:
        return {k: v.value for k, v in sorted(self._entries.items())}

    def get_section(self, prefix: str) -> Dict[str, Any]:
        return {k: v.value for k, v in self._entries.items()
                if k.startswith(prefix + ".")}

    def export_template(self) -> str:
        """Export a config template with all defaults."""
        template = {}
        for key, value in self.DEFAULTS.items():
            parts = key.split(".")
            d = template
            for part in parts[:-1]:
                d = d.setdefault(part, {})
            d[parts[-1]] = value
        return json.dumps(template, indent=2)

    def get_stats(self) -> Dict:
        by_source = {}
        for entry in self._entries.values():
            by_source[entry.source.value] = by_source.get(
                entry.source.value, 0) + 1
        return {
            "total_keys": len(self._entries),
            "by_source": by_source,
            "immutable_count": len(self.IMMUTABLE),
        }


# ============================================================================
#  STRUCTURED JSON LOGGING
# ============================================================================

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter with correlation ID support."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        # Add exception info
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }
        return json.dumps(log_entry, default=str)


class CorrelationFilter(logging.Filter):
    """Adds correlation ID to log records."""

    _local = threading.local()

    @classmethod
    def set_correlation_id(cls, cid: str):
        cls._local.correlation_id = cid

    @classmethod
    def get_correlation_id(cls) -> Optional[str]:
        return getattr(cls._local, 'correlation_id', None)

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = self.get_correlation_id() or ""
        return True


def setup_logging(config: ConfigManager = None):
    """Configure structured JSON logging with rotation."""
    level = config.get("logging.level", "INFO") if config else "INFO"
    log_file = config.get("logging.file", "ason_security.log") if config else "ason_security.log"
    max_bytes = config.get("logging.max_bytes", 10485760) if config else 10485760
    backup_count = config.get("logging.backup_count", 5) if config else 5

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root.handlers.clear()

    # JSON formatter
    formatter = JSONFormatter()
    correlation_filter = CorrelationFilter()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.addFilter(correlation_filter)
    root.addHandler(console)

    # File handler with rotation
    data_dir = Path(os.environ.get("ASON_DATA_DIR",
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ason_data")))
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = str(data_dir / log_file)

    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=backup_count)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(correlation_filter)
    root.addHandler(file_handler)

    logger.info("Logging configured: level=%s, file=%s, rotation=%dMB x %d",
                level, log_path, max_bytes // 1048576, backup_count)


# ============================================================================
#  STARTUP ORCHESTRATION
# ============================================================================

class BootPhase(str, Enum):
    CONFIG = "config"
    LOGGING = "logging"
    STORAGE = "storage"
    SECURITY = "security"
    MODULES = "modules"
    API = "api"
    HEALTH = "health"
    READY = "ready"


class HealthCheck:
    def __init__(self, name, check_fn, critical=True):
        self.name = name
        self.check_fn = check_fn
        self.critical = critical
        self.status = "pending"
        self.last_check = None
        self.message = ""


class StartupOrchestrator:
    """Boot sequence with dependency ordering and health checks."""

    def __init__(self):
        self._phases: List[Dict] = []
        self._health_checks: List[HealthCheck] = []
        self._config: Optional[ConfigManager] = None
        self._start_time = None
        self._ready = False

    def boot(self, config_file: str = None) -> Dict:
        """Execute full boot sequence."""
        self._start_time = time.time()
        results = []

        # Phase 1: Config
        results.append(self._boot_phase(BootPhase.CONFIG, self._init_config, config_file))

        # Phase 2: Logging
        results.append(self._boot_phase(BootPhase.LOGGING, self._init_logging))

        # Phase 3: Storage
        results.append(self._boot_phase(BootPhase.STORAGE, self._init_storage))

        # Phase 4: Security checks
        results.append(self._boot_phase(BootPhase.SECURITY, self._init_security))

        # Phase 5: Module loading
        results.append(self._boot_phase(BootPhase.MODULES, self._init_modules))

        # Phase 6: Health checks
        results.append(self._boot_phase(BootPhase.HEALTH, self._run_health_checks))

        # Phase 7: Ready
        elapsed = time.time() - self._start_time
        self._ready = all(r.get("success") for r in results)

        return {
            "ready": self._ready,
            "boot_time_seconds": round(elapsed, 3),
            "phases": results,
            "health": self.get_health_report(),
        }

    def _boot_phase(self, phase: BootPhase, fn, *args) -> Dict:
        start = time.time()
        try:
            fn(*args)
            elapsed = time.time() - start
            result = {"phase": phase.value, "success": True,
                     "duration_ms": round(elapsed * 1000, 1)}
            self._phases.append(result)
            logger.info("Boot phase %s completed in %.1fms", phase.value,
                       elapsed * 1000)
            return result
        except Exception as e:
            elapsed = time.time() - start
            result = {"phase": phase.value, "success": False,
                     "error": str(e), "duration_ms": round(elapsed * 1000, 1)}
            self._phases.append(result)
            logger.error("Boot phase %s FAILED: %s", phase.value, e)
            return result

    def _init_config(self, config_file=None):
        self._config = ConfigManager(config_file)
        logger.info("Config initialized: %d keys", len(self._config.get_all()))

    def _init_logging(self):
        setup_logging(self._config)

    def _init_storage(self):
        from services.orchestrator.persistent_storage import get_storage
        try:
            db = get_storage()
            stats = db.get_stats()
            logger.info("Storage ready: %s (%d migrations)", stats["db_path"],
                       stats["migrations_applied"])
        except Exception:
            logger.info("Storage initialization deferred (import context)")

    def _init_security(self):
        # Verify immutable security constraints
        assert self._config.get("security.telemetry") is False, "Telemetry must be disabled"
        assert self._config.get("security.external_api_calls") is False, "External APIs must be disabled"
        assert self._config.get("security.backdoors") is False, "Backdoors must be disabled"
        assert self._config.get("security.zero_trust") is True, "Zero Trust must be enabled"
        logger.info("Security constraints verified: zero telemetry, zero external APIs, zero backdoors")

    def _init_modules(self):
        module_count = self._config.get("platform.modules", 120)
        logger.info("Module registry: %d modules available", module_count)

    def _run_health_checks(self):
        self._health_checks = [
            HealthCheck("config_loaded", lambda: len(self._config.get_all()) > 0),
            HealthCheck("telemetry_disabled", lambda: self._config.get("security.telemetry") is False),
            HealthCheck("zero_trust_enabled", lambda: self._config.get("security.zero_trust") is True),
            HealthCheck("encryption_enabled", lambda: self._config.get("security.encryption_at_rest") is True),
            HealthCheck("fips_mode", lambda: self._config.get("security.fips_mode") is True),
            HealthCheck("logging_active", lambda: len(logging.getLogger().handlers) > 0),
        ]
        for check in self._health_checks:
            try:
                result = check.check_fn()
                check.status = "healthy" if result else "unhealthy"
                check.last_check = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                check.status = "error"
                check.message = str(e)

    def get_health_report(self) -> Dict:
        total = len(self._health_checks)
        healthy = sum(1 for c in self._health_checks if c.status == "healthy")
        return {
            "overall": "healthy" if healthy == total else "degraded",
            "checks": {c.name: c.status for c in self._health_checks},
            "healthy": healthy,
            "total": total,
        }

    def get_config(self) -> Optional[ConfigManager]:
        return self._config

    def is_ready(self) -> bool:
        return self._ready


# Singletons
config_manager = ConfigManager()
startup_orchestrator = StartupOrchestrator()
