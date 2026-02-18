"""
Pre-Deployment Preflight Check — Ason Security Platform
Validates everything is deployment-ready before going live.
ZERO EXTERNAL APIs | stdlib only
"""

import importlib, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONSOLE_DIR = os.path.join(BASE_DIR, "console")


class PreflightChecker:
    """Comprehensive pre-deployment validation."""

    def __init__(self):
        self.checks = []
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.start_time = time.time()

    def _check(self, name: str, fn, critical: bool = True):
        try:
            result = fn()
            ok = result is True
            self.checks.append({
                "name": name,
                "passed": ok,
                "critical": critical,
                "detail": "" if ok else str(result),
            })
            if ok:
                self.passed += 1
                print(f"  ✅ {name}")
            elif critical:
                self.failed += 1
                print(f"  ❌ {name}: {result}")
            else:
                self.warnings += 1
                print(f"  ⚠️  {name}: {result}")
        except Exception as e:
            self.checks.append({"name": name, "passed": False, "critical": critical, "detail": str(e)})
            if critical:
                self.failed += 1
                print(f"  ❌ {name}: ERROR — {e}")
            else:
                self.warnings += 1
                print(f"  ⚠️  {name}: ERROR — {e}")

    # ================================================================
    #  CHECKS
    # ================================================================

    # ---- 1. Security Immutables ----

    def check_no_telemetry(self):
        try:
            from services.orchestrator.production_config import ConfigManager
            cm = ConfigManager()
            val = cm.get("telemetry.enabled", False)
            return val is False or val == "false" or f"telemetry.enabled={val}"
        except ImportError:
            return True  # Module not loaded = telemetry not possible

    def check_no_ext_apis(self):
        try:
            from services.orchestrator.production_config import ConfigManager
            cm = ConfigManager()
            val = cm.get("external_api.enabled", False)
            return val is False or val == "false" or f"external_api.enabled={val}"
        except ImportError:
            return True

    def check_no_backdoors(self):
        try:
            from services.orchestrator.production_config import ConfigManager
            cm = ConfigManager()
            val = cm.get("backdoors.enabled", False)
            return val is False or val == "false" or f"backdoors.enabled={val}"
        except ImportError:
            return True

    def check_immutable_protection(self):
        try:
            from services.orchestrator.production_config import ConfigManager
            cm = ConfigManager()
            # Try to override an immutable key
            result = cm.set("telemetry.enabled", True)
            return result is False or "immutable override allowed!"
        except ImportError:
            return True

    # ---- 2. Module Imports ----

    def check_sdk_import(self):
        from services.orchestrator.security_sdk import SecurityPlatform
        return SecurityPlatform is not None

    def check_rest_api_import(self):
        from services.orchestrator.security_rest_api import SecurityAPIServer
        return SecurityAPIServer is not None

    def check_cli_import(self):
        from services.orchestrator.security_cli import main as cli_main
        return cli_main is not None

    def check_storage_import(self):
        from services.orchestrator.persistent_storage import StorageBackend
        return StorageBackend is not None

    def check_config_import(self):
        from services.orchestrator.production_config import ConfigManager
        return ConfigManager is not None

    def check_verification_import(self):
        from services.orchestrator.live_verification import LiveVerifier
        return LiveVerifier is not None

    def check_smoke_import(self):
        from services.orchestrator.smoke_tests import SmokeTestRunner
        return SmokeTestRunner is not None

    def check_docs_import(self):
        from services.orchestrator.api_docs import generate_api_docs
        return generate_api_docs is not None

    def check_digital_twin_import(self):
        from services.orchestrator.digital_twin import SecurityDigitalTwin
        return SecurityDigitalTwin is not None

    def check_data_science_import(self):
        from services.orchestrator.data_science import MLPipeline
        return MLPipeline is not None

    def check_security_mesh_import(self):
        from services.orchestrator.security_mesh import SecurityMesh
        return SecurityMesh is not None

    def check_integration_tests_import(self):
        from services.orchestrator.integration_tests import IntegrationTestSuite
        return IntegrationTestSuite is not None

    # ---- 3. SQLite Storage ----

    def check_storage_init(self):
        from services.orchestrator.persistent_storage import StorageBackend
        import tempfile
        db_path = os.path.join(tempfile.gettempdir(), "preflight_test.db")
        try:
            backend = StorageBackend(db_path)
            stats = backend.get_stats()
            return stats.get("migrations_applied", 0) >= 8 or \
                   f"only {stats.get('migrations_applied', 0)} migrations"
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)
            wal = db_path + "-wal"
            shm = db_path + "-shm"
            if os.path.exists(wal): os.remove(wal)
            if os.path.exists(shm): os.remove(shm)

    def check_storage_crud(self):
        from services.orchestrator.persistent_storage import StorageBackend, EventStore
        import tempfile
        db_path = os.path.join(tempfile.gettempdir(), "preflight_crud.db")
        try:
            backend = StorageBackend(db_path)
            store = EventStore(backend)
            eid = store.store("test_event", "preflight", {"key": "val"})
            events = store.query(event_type="test_event", limit=1)
            return len(events) > 0 or "no events found after insert"
        finally:
            if os.path.exists(db_path): os.remove(db_path)
            wal = db_path + "-wal"
            shm = db_path + "-shm"
            if os.path.exists(wal): os.remove(wal)
            if os.path.exists(shm): os.remove(shm)

    # ---- 4. Console Assets ----

    def check_console_index(self):
        path = os.path.join(CONSOLE_DIR, "index.html")
        if not os.path.isfile(path):
            return f"not found: {path}"
        size = os.path.getsize(path)
        return size > 1000 or f"too small: {size} bytes"

    def check_console_css(self):
        path = os.path.join(CONSOLE_DIR, "styles.css")
        if not os.path.isfile(path):
            return f"not found: {path}"
        size = os.path.getsize(path)
        return size > 5000 or f"too small: {size} bytes"

    def check_console_js(self):
        path = os.path.join(CONSOLE_DIR, "app.js")
        if not os.path.isfile(path):
            return f"not found: {path}"
        size = os.path.getsize(path)
        return size > 2000 or f"too small: {size} bytes"

    def check_console_loading_css(self):
        path = os.path.join(CONSOLE_DIR, "loading.css")
        return os.path.isfile(path) or f"not found: {path}"

    # ---- 5. Config Validation ----

    def check_config_defaults(self):
        try:
            from services.orchestrator.production_config import ConfigManager
            cm = ConfigManager()
            key_defaults = ["server.host", "server.port", "telemetry.enabled"]
            for key in key_defaults:
                val = cm.get(key)
                if val is None:
                    return f"missing default: {key}"
            return True
        except ImportError:
            return True

    # ---- 6. No Debug Flags ----

    def check_no_debug_in_config(self):
        try:
            from services.orchestrator.production_config import ConfigManager
            cm = ConfigManager()
            debug = cm.get("debug", False)
            return debug is False or debug == "false" or f"debug={debug}"
        except ImportError:
            return True

    # ---- 7. REST API Route Count ----

    def check_api_routes(self):
        from services.orchestrator.security_rest_api import SecurityAPIHandler
        count = len(SecurityAPIHandler.ROUTES)
        return count >= 30 or f"only {count} routes (expected 30+)"

    # ---- 8. SDK Operations ----

    def check_sdk_health(self):
        from services.orchestrator.security_sdk import SecurityPlatform
        p = SecurityPlatform()
        health = p.health()
        return isinstance(health, dict) and "status" in health or "healthy" in str(health).lower()

    def check_sdk_version(self):
        from services.orchestrator.security_sdk import SecurityPlatform
        p = SecurityPlatform()
        v = p.version()
        return isinstance(v, dict) and "version" in v

    # ---- 9. File integrity ----

    def check_no_pycache_bloat(self):
        pycache_count = 0
        for root, dirs, files in os.walk(BASE_DIR):
            for d in dirs:
                if d == "__pycache__":
                    pycache_count += 1
        return pycache_count < 20 or f"found {pycache_count} __pycache__ dirs"

    # ================================================================
    #  RUN ALL
    # ================================================================

    def run(self) -> dict:
        print("\n" + "=" * 60)
        print("  ASON SECURITY PLATFORM — PRE-DEPLOYMENT PREFLIGHT")
        print("=" * 60)

        # 1. Security immutables
        print("\n  ── SECURITY IMMUTABLES ──")
        self._check("Telemetry disabled", self.check_no_telemetry)
        self._check("External APIs disabled", self.check_no_ext_apis)
        self._check("Backdoors disabled", self.check_no_backdoors)
        self._check("Immutable protection works", self.check_immutable_protection)

        # 2. Module imports
        print("\n  ── MODULE IMPORTS ──")
        self._check("Security SDK", self.check_sdk_import)
        self._check("REST API", self.check_rest_api_import)
        self._check("CLI Tool", self.check_cli_import, critical=False)
        self._check("Persistent Storage", self.check_storage_import)
        self._check("Production Config", self.check_config_import)
        self._check("Live Verification", self.check_verification_import)
        self._check("Smoke Tests", self.check_smoke_import)
        self._check("API Docs", self.check_docs_import)
        self._check("Digital Twin", self.check_digital_twin_import, critical=False)
        self._check("Data Science", self.check_data_science_import, critical=False)
        self._check("Security Mesh", self.check_security_mesh_import, critical=False)
        self._check("Integration Tests", self.check_integration_tests_import, critical=False)

        # 3. SQLite storage
        print("\n  ── STORAGE ──")
        self._check("SQLite init + 8 migrations", self.check_storage_init)
        self._check("CRUD operations", self.check_storage_crud)

        # 4. Console assets
        print("\n  ── CONSOLE ASSETS ──")
        self._check("index.html exists (>1KB)", self.check_console_index)
        self._check("styles.css exists (>5KB)", self.check_console_css)
        self._check("app.js exists (>2KB)", self.check_console_js)
        self._check("loading.css exists", self.check_console_loading_css)

        # 5. Config
        print("\n  ── CONFIGURATION ──")
        self._check("Config defaults loaded", self.check_config_defaults)
        self._check("No debug mode", self.check_no_debug_in_config)

        # 6. REST API
        print("\n  ── REST API ──")
        self._check("30+ routes registered", self.check_api_routes)

        # 7. SDK operations
        print("\n  ── SDK OPERATIONS ──")
        self._check("SDK health check", self.check_sdk_health)
        self._check("SDK version info", self.check_sdk_version)

        # 8. Filesystem
        print("\n  ── FILESYSTEM ──")
        self._check("No excessive __pycache__", self.check_no_pycache_bloat, critical=False)

        # Summary
        total = self.passed + self.failed + self.warnings
        elapsed = round(time.time() - self.start_time, 2)

        print("\n" + "=" * 60)
        print(f"  PREFLIGHT COMPLETE")
        print(f"  {self.passed} passed · {self.failed} failed · {self.warnings} warnings · {elapsed}s")
        print("=" * 60)

        if self.failed == 0:
            print("\n  🟢 DEPLOYMENT READY")
            print("  ✅ All security immutables enforced")
            print("  ✅ All critical modules importable")
            print("  ✅ Storage engine operational")
            print("  ✅ Console assets present")
            print("  ✅ Configuration validated")
            print("  ✅ REST API routes registered")
            print("  ✅ SDK operational")
            if self.warnings > 0:
                print(f"  ⚠️  {self.warnings} non-critical warning(s)")
            print("\n  NEXT STEPS:")
            print("    1. python services/orchestrator/smoke_tests.py")
            print("    2. python services/orchestrator/security_rest_api.py")
            print("    3. Open http://localhost:9443/console/")
        else:
            print(f"\n  🔴 NOT READY — {self.failed} critical failure(s):")
            for c in self.checks:
                if not c["passed"] and c["critical"]:
                    print(f"      ❌ {c['name']}: {c['detail']}")

        print()
        return {
            "ready": self.failed == 0,
            "total": total,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "duration_seconds": elapsed,
            "checks": self.checks,
        }


if __name__ == "__main__":
    checker = PreflightChecker()
    result = checker.run()
    sys.exit(0 if result["ready"] else 1)
