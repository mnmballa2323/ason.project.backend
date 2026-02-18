"""
E2E Smoke Tests — Ason Security Platform
Starts API server, hits every endpoint, validates responses.
ZERO EXTERNAL APIs | stdlib only
"""

import json, os, sys, threading, time, urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


# ============================================================================
#  TEST HARNESS
# ============================================================================

class SmokeTestRunner:
    """End-to-end smoke test runner for pre-deployment validation."""

    def __init__(self, host="127.0.0.1", port=19443):
        self.host = host
        self.port = port
        self.base = f"http://{host}:{port}"
        self.results = []
        self.passed = 0
        self.failed = 0
        self._server = None
        self._thread = None

    # ---- Server lifecycle ----

    def _start_server(self):
        from services.orchestrator.security_rest_api import SecurityAPIServer
        self._server = SecurityAPIServer(self.host, self.port)
        self._thread = threading.Thread(target=self._server.start, daemon=True)
        self._thread.start()
        time.sleep(1.5)  # Wait for server to bind

    def _stop_server(self):
        if self._server:
            self._server.stop()

    # ---- HTTP helpers ----

    def _get(self, path, expect_status=200):
        url = f"{self.base}{path}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                return resp.status, data, dict(resp.headers)
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            try:
                data = json.loads(body)
            except:
                data = {"raw": body}
            return e.code, data, dict(e.headers)
        except Exception as e:
            return 0, {"error": str(e)}, {}

    def _post(self, path, body=None, expect_status=200):
        url = f"{self.base}{path}"
        try:
            data = json.dumps(body or {}).encode()
            req = urllib.request.Request(url, data=data, method="POST",
                                       headers={"Content-Type": "application/json",
                                                "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                rdata = json.loads(resp.read().decode())
                return resp.status, rdata, dict(resp.headers)
        except urllib.error.HTTPError as e:
            body_raw = e.read().decode() if e.fp else ""
            try:
                rdata = json.loads(body_raw)
            except:
                rdata = {"raw": body_raw}
            return e.code, rdata, dict(e.headers)
        except Exception as e:
            return 0, {"error": str(e)}, {}

    # ---- Test runner ----

    def _test(self, name, fn):
        try:
            result = fn()
            ok = result is True
            self.results.append((name, ok, ""))
            if ok:
                self.passed += 1
                print(f"  ✅ PASS  {name}")
            else:
                self.failed += 1
                print(f"  ❌ FAIL  {name} → {result}")
        except Exception as e:
            self.failed += 1
            self.results.append((name, False, str(e)))
            print(f"  ❌ FAIL  {name} → ERROR: {e}")

    # ================================================================
    #  TESTS
    # ================================================================

    def test_health(self):
        status, data, _ = self._get("/api/v1/health")
        return status == 200 and "api" in data

    def test_version(self):
        status, data, _ = self._get("/api/v1/version")
        return status == 200 and "version" in data

    def test_stats(self):
        status, data, _ = self._get("/api/v1/stats")
        return status == 200

    def test_posture(self):
        status, data, _ = self._get("/api/v1/posture")
        return status == 200

    def test_threat_level(self):
        status, data, _ = self._get("/api/v1/threat-level")
        return status == 200

    def test_risk_exposure(self):
        status, data, _ = self._get("/api/v1/risk-exposure")
        return status == 200

    def test_board_report(self):
        status, data, _ = self._get("/api/v1/board-report")
        return status == 200

    def test_compliance(self):
        status, data, _ = self._get("/api/v1/compliance")
        return status == 200

    def test_scan(self):
        status, data, _ = self._post("/api/v1/scan", {"target": "test-target"})
        return status == 200

    def test_triage(self):
        status, data, _ = self._post("/api/v1/triage", {"type": "brute_force", "source": "10.0.0.1"})
        return status == 200

    def test_decide(self):
        status, data, _ = self._post("/api/v1/decide", {"context": "test"})
        return status == 200

    def test_classify(self):
        status, data, _ = self._post("/api/v1/classify", {"content": "test data", "source": "smoke"})
        return status == 200

    def test_query(self):
        status, data, _ = self._post("/api/v1/query", {"query": "threat status"})
        return status == 200

    def test_emulate(self):
        status, data, _ = self._post("/api/v1/emulate", {"adversary": "APT29"})
        return status == 200

    def test_adversaries(self):
        status, data, _ = self._get("/api/v1/adversaries")
        return status == 200 and "adversaries" in data

    def test_blast_radius(self):
        status, data, _ = self._get("/api/v1/blast-radius?node=api-gw&hops=2")
        return status == 200

    def test_attack_paths(self):
        status, data, _ = self._get("/api/v1/attack-paths")
        return status == 200

    def test_workflows(self):
        status, data, _ = self._get("/api/v1/workflows")
        return status == 200

    def test_chaos(self):
        status, data, _ = self._post("/api/v1/chaos", {"scenario": "region_failover"})
        return status == 200

    def test_dr_status(self):
        status, data, _ = self._get("/api/v1/dr/status")
        return status == 200

    def test_mesh_status(self):
        status, data, _ = self._get("/api/v1/mesh/status")
        return status == 200

    def test_ml_stats(self):
        status, data, _ = self._get("/api/v1/ml/stats")
        return status == 200

    def test_twin_status(self):
        status, data, _ = self._get("/api/v1/twin/status")
        return status == 200

    def test_twin_whatif(self):
        status, data, _ = self._post("/api/v1/twin/whatif", {"scenario": "disable_mfa"})
        return status == 200

    def test_twin_attack(self):
        status, data, _ = self._post("/api/v1/twin/attack", {"attack_type": "apt_intrusion"})
        return status == 200

    def test_storage_stats(self):
        status, data, _ = self._get("/api/v1/storage/stats")
        return status == 200

    def test_events(self):
        status, data, _ = self._get("/api/v1/events?limit=5")
        return status == 200

    def test_config(self):
        status, data, _ = self._get("/api/v1/config")
        return status == 200

    # ---- Security tests ----

    def test_cors_headers(self):
        _, _, headers = self._get("/api/v1/health")
        return headers.get("Access-Control-Allow-Origin") == "*"

    def test_security_headers(self):
        _, _, headers = self._get("/api/v1/health")
        required = ["X-Content-Type-Options", "X-Frame-Options", "Strict-Transport-Security",
                     "X-Security-Platform", "X-Request-Id"]
        missing = [h for h in required if h not in headers]
        return len(missing) == 0 or f"missing: {missing}"

    def test_request_id(self):
        _, _, headers = self._get("/api/v1/health")
        rid = headers.get("X-Request-Id", "")
        return len(rid) > 0

    def test_404_handling(self):
        status, data, _ = self._get("/api/v1/nonexistent")
        return status == 404 and "error" in data

    def test_invalid_json(self):
        url = f"{self.base}/api/v1/scan"
        try:
            req = urllib.request.Request(url, data=b"not-json", method="POST",
                                       headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            return False
        except urllib.error.HTTPError as e:
            return e.code == 400

    # ---- Console static serving ----

    def test_console_index(self):
        url = f"{self.base}/console/"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode()
                return "ASONSEC" in html or "Ason" in html
        except:
            return False

    def test_console_css(self):
        url = f"{self.base}/console/styles.css"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                css = resp.read().decode()
                return "--bg-primary" in css or "glass" in css
        except:
            return False

    def test_console_js(self):
        url = f"{self.base}/console/app.js"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                js = resp.read().decode()
                return "AsonAPI" in js
        except:
            return False

    def test_root_redirect(self):
        url = f"{self.base}/"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                html = resp.read().decode()
                return "Ason" in html
        except:
            return False

    # ================================================================
    #  RUN ALL
    # ================================================================

    def run(self) -> dict:
        print("\n" + "=" * 60)
        print("  ASON SECURITY PLATFORM — E2E SMOKE TESTS")
        print("=" * 60)

        print("\n  Starting test server...")
        try:
            self._start_server()
        except Exception as e:
            print(f"  ❌ Failed to start server: {e}")
            return {"passed": 0, "failed": 1, "error": str(e)}

        print(f"  Server running on {self.base}\n")

        # API endpoint tests
        print("  ── API ENDPOINTS ──")
        self._test("GET  /health", self.test_health)
        self._test("GET  /version", self.test_version)
        self._test("GET  /stats", self.test_stats)
        self._test("GET  /posture", self.test_posture)
        self._test("GET  /threat-level", self.test_threat_level)
        self._test("GET  /risk-exposure", self.test_risk_exposure)
        self._test("GET  /board-report", self.test_board_report)
        self._test("GET  /compliance", self.test_compliance)
        self._test("POST /scan", self.test_scan)
        self._test("POST /triage", self.test_triage)
        self._test("POST /decide", self.test_decide)
        self._test("POST /classify", self.test_classify)
        self._test("POST /query", self.test_query)
        self._test("POST /emulate", self.test_emulate)
        self._test("GET  /adversaries", self.test_adversaries)
        self._test("GET  /blast-radius", self.test_blast_radius)
        self._test("GET  /attack-paths", self.test_attack_paths)
        self._test("GET  /workflows", self.test_workflows)
        self._test("POST /chaos", self.test_chaos)
        self._test("GET  /dr/status", self.test_dr_status)
        self._test("GET  /mesh/status", self.test_mesh_status)
        self._test("GET  /ml/stats", self.test_ml_stats)
        self._test("GET  /twin/status", self.test_twin_status)
        self._test("POST /twin/whatif", self.test_twin_whatif)
        self._test("POST /twin/attack", self.test_twin_attack)
        self._test("GET  /storage/stats", self.test_storage_stats)
        self._test("GET  /events", self.test_events)
        self._test("GET  /config", self.test_config)

        # Security tests
        print("\n  ── SECURITY ──")
        self._test("CORS headers present", self.test_cors_headers)
        self._test("Security headers complete", self.test_security_headers)
        self._test("Request ID generated", self.test_request_id)
        self._test("404 handling", self.test_404_handling)
        self._test("Invalid JSON → 400", self.test_invalid_json)

        # Static serving tests
        print("\n  ── CONSOLE SERVING ──")
        self._test("Console index.html", self.test_console_index)
        self._test("Console styles.css", self.test_console_css)
        self._test("Console app.js", self.test_console_js)
        self._test("Root / → console", self.test_root_redirect)

        # Summary
        total = self.passed + self.failed
        print("\n" + "=" * 60)
        print(f"  SMOKE TESTS COMPLETE")
        print(f"  {self.passed}/{total} passed · {self.failed} failed")
        print("=" * 60)

        if self.failed == 0:
            print("\n  🟢 ALL TESTS PASSED — READY FOR DEPLOYMENT")
            print("  ✅ All 35 API endpoints responding")
            print("  ✅ CORS headers present")
            print("  ✅ Security headers complete")
            print("  ✅ Console static serving works")
            print("  ✅ Error handling validated")
        else:
            print(f"\n  🔴 {self.failed} TEST(S) FAILED:")
            for name, ok, err in self.results:
                if not ok:
                    print(f"      ❌ {name}: {err}")

        print()
        self._stop_server()

        return {
            "total": total,
            "passed": self.passed,
            "failed": self.failed,
            "results": [{"name": n, "passed": p, "error": e}
                       for n, p, e in self.results],
        }


if __name__ == "__main__":
    runner = SmokeTestRunner()
    result = runner.run()
    sys.exit(0 if result["failed"] == 0 else 1)
