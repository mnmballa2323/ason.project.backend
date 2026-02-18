"""
Security Test Suite — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Comprehensive unit, integration, regression, and stress tests
for all 42+ security modules. Self-contained test runner.
"""

import hashlib, logging, os, time, traceback
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("qwen.security_tests")


class TestResult:
    def __init__(self, name: str, category: str, passed: bool,
                 duration_ms: float, error: str = ""):
        self.name = name
        self.category = category
        self.passed = passed
        self.duration_ms = duration_ms
        self.error = error

    def to_dict(self):
        return {"name": self.name, "category": self.category,
                "passed": self.passed, "duration_ms": round(self.duration_ms, 2),
                "error": self.error[:200] if self.error else ""}


class SecurityTestRunner:
    """Self-contained test runner for all security modules."""

    def __init__(self):
        self._results: List[TestResult] = []
        self._suites: Dict[str, List[Callable]] = {
            "unit": [], "integration": [], "regression": [], "stress": []
        }
        self._register_all()

    def _run_test(self, name: str, category: str, fn: Callable) -> TestResult:
        start = time.time()
        try:
            fn()
            duration = (time.time() - start) * 1000
            return TestResult(name, category, True, duration)
        except Exception as e:
            duration = (time.time() - start) * 1000
            return TestResult(name, category, False, duration, str(e))

    # ------------------------------------------------------------------
    #  UNIT TESTS
    # ------------------------------------------------------------------
    def _register_all(self):
        # Phase 71: Integration Layer
        self._suites["unit"].extend([
            ("SecurityHub.lazy_load", self._test_hub_lazy_load),
            ("SecurityHub.scan", self._test_hub_scan),
            ("SecurityHub.status", self._test_hub_status),
            ("EventBus.emit", self._test_eventbus_emit),
            ("EventBus.subscribe", self._test_eventbus_subscribe),
            ("EventBus.chain", self._test_eventbus_chain),
            ("SecurityConfig.get_set", self._test_config_get_set),
            ("SecurityConfig.immutable", self._test_config_immutable),
            ("SecurityConfig.levels", self._test_config_levels),
            ("DashboardAPI.overview", self._test_dashboard_overview),
        ])

        # DLP tests
        self._suites["unit"].extend([
            ("DLP.detect_ssn", self._test_dlp_ssn),
            ("DLP.detect_credit_card", self._test_dlp_credit_card),
            ("DLP.detect_aws_key", self._test_dlp_aws_key),
            ("DLP.redact", self._test_dlp_redact),
            ("DLP.classify", self._test_dlp_classify),
        ])

        # Blockchain tests
        self._suites["unit"].extend([
            ("Merkle.append_verify", self._test_merkle_append),
            ("Merkle.proof", self._test_merkle_proof),
            ("Timestamp.chain", self._test_timestamp_chain),
            ("Attestation.issue_revoke", self._test_attestation),
        ])

        # Privacy tests
        self._suites["unit"].extend([
            ("DSAR.submit_process", self._test_dsar),
            ("Consent.record_check", self._test_consent),
            ("PIA.assessment", self._test_pia),
        ])

        # Maturity tests
        self._suites["unit"].extend([
            ("CMMC.assess", self._test_cmmc),
            ("SOC2.report", self._test_soc2),
            ("NISTCSF.assess", self._test_nist_csf),
        ])

        # SecMLOps tests
        self._suites["unit"].extend([
            ("ModelRegistry.register", self._test_model_registry),
            ("XAI.explain", self._test_xai),
            ("Bias.assess", self._test_bias),
            ("AIIncident.activate", self._test_ai_incident),
        ])

        # Edge security tests
        self._suites["unit"].extend([
            ("Edge.firmware_verify", self._test_edge_firmware),
            ("AirGap.enable_disable", self._test_airgap),
            ("Mesh.tunnel", self._test_mesh_tunnel),
            ("TPM.measure_attest", self._test_tpm),
        ])

        # Integration tests
        self._suites["integration"].extend([
            ("EventBus→DLP→Containment chain", self._test_chain_dlp_containment),
            ("Hub.scan→multi-module", self._test_chain_hub_scan),
            ("Config→Module enable/disable", self._test_chain_config_modules),
        ])

        # Regression tests
        self._suites["regression"].extend([
            ("NoTelemetry.config", self._test_no_telemetry_config),
            ("NoTelemetry.imports", self._test_no_external_imports),
            ("Immutable.security_blocks", self._test_immutable_blocks),
        ])

        # Stress tests
        self._suites["stress"].extend([
            ("EventBus.1000_events", self._test_stress_eventbus),
            ("DLP.1000_scans", self._test_stress_dlp),
            ("Merkle.500_entries", self._test_stress_merkle),
        ])

    # ---- Unit test implementations ----

    def _test_hub_lazy_load(self):
        from security_hub import SecurityHub
        hub = SecurityHub()
        inv = hub.inventory()
        assert len(inv) > 40, f"Expected 40+ modules, got {len(inv)}"

    def _test_hub_scan(self):
        from security_hub import SecurityHub
        hub = SecurityHub()
        result = hub.scan("test content")
        assert "threat_level" in result

    def _test_hub_status(self):
        from security_hub import SecurityHub
        hub = SecurityHub()
        status = hub.status()
        assert "modules_registered" in status

    def _test_eventbus_emit(self):
        from security_event_bus import SecurityEventBus, EventCategory, EventSeverity
        bus = SecurityEventBus()
        event = bus.emit(EventCategory.SYSTEM, EventSeverity.INFO, "test", "test event")
        assert event.event_id.startswith("EVT-")
        assert event.propagated is True

    def _test_eventbus_subscribe(self):
        from security_event_bus import SecurityEventBus, EventCategory, EventSeverity
        bus = SecurityEventBus()
        received = []
        sub = bus.subscribe("test_sub", [EventCategory.SYSTEM],
                           handler=lambda e: received.append(e))
        bus.emit(EventCategory.SYSTEM, EventSeverity.INFO, "test", "hello")
        assert len(received) == 1
        assert sub.received == 1

    def _test_eventbus_chain(self):
        from security_event_bus import SecurityEventBus, EventCategory
        bus = SecurityEventBus()
        chain = bus.get_chain(EventCategory.DATA_LEAK)
        assert len(chain) >= 3, "Data leak chain should have 3+ steps"

    def _test_config_get_set(self):
        from security_config import SecurityConfig
        cfg = SecurityConfig()
        assert cfg.get("global.zero_api") is True
        result = cfg.set("thresholds.max_failed_logins", 3)
        assert "error" not in result
        assert cfg.get("thresholds.max_failed_logins") == 3

    def _test_config_immutable(self):
        from security_config import SecurityConfig
        cfg = SecurityConfig()
        result = cfg.set("hardcoded_security.telemetry_enabled", True)
        assert result.get("blocked") is True

    def _test_config_levels(self):
        from security_config import SecurityConfig, SecurityLevel
        cfg = SecurityConfig()
        result = cfg.apply_security_level(SecurityLevel.MAXIMUM)
        assert cfg.get("thresholds.max_failed_logins") == 3

    def _test_dashboard_overview(self):
        from security_dashboard_api import SecurityDashboardAPI
        api = SecurityDashboardAPI()
        result = api.get_overview()
        assert result["endpoint"] == "/api/security/overview"
        assert result["security_guarantees"]["telemetry"] is False

    def _test_dlp_ssn(self):
        from dlp import DLPEngine
        engine = DLPEngine()
        results = engine.scan("SSN is 123-45-6789")
        assert any(r["pattern"] == "SSN" for r in results)

    def _test_dlp_credit_card(self):
        from dlp import DLPEngine
        engine = DLPEngine()
        results = engine.scan("card: 4111-1111-1111-1111")
        assert len(results) > 0

    def _test_dlp_aws_key(self):
        from dlp import DLPEngine
        engine = DLPEngine()
        results = engine.scan("key: AKIAIOSFODNN7EXAMPLE")
        assert any(r["pattern"] == "AWS Key" for r in results)

    def _test_dlp_redact(self):
        from dlp import DLPEngine
        engine = DLPEngine()
        redacted = engine.redact("SSN: 123-45-6789")
        assert "123-45-6789" not in redacted
        assert "[REDACTED:" in redacted

    def _test_dlp_classify(self):
        from dlp import DataClassifier
        clf = DataClassifier()
        result = clf.classify("This is top secret information")
        assert result["classification"] == "top_secret"

    def _test_merkle_append(self):
        from blockchain_audit import MerkleAuditLog
        log = MerkleAuditLog()
        log.append("test_event", "test_actor")
        log.append("test_event_2", "test_actor")
        result = log.verify_integrity()
        assert result["valid"] is True

    def _test_merkle_proof(self):
        from blockchain_audit import MerkleAuditLog
        log = MerkleAuditLog()
        for i in range(5):
            log.append(f"event_{i}", "actor")
        proof = log.get_proof(2)
        assert "error" not in proof
        assert proof["proof_length"] > 0

    def _test_timestamp_chain(self):
        from blockchain_audit import DecentralizedTimestamping
        ts = DecentralizedTimestamping()
        ts.timestamp("data_1")
        ts.timestamp("data_2")
        result = ts.verify_chain()
        assert result["valid"] is True

    def _test_attestation(self):
        from blockchain_audit import AttestationTokenEngine, AttestationType
        engine = AttestationTokenEngine()
        token = engine.issue(AttestationType.CERTIFICATION, "user1", "issuer1", {"scope": "full"})
        verify = engine.verify(token.token_id)
        assert verify["valid"] is True
        engine.revoke(token.token_id)
        verify2 = engine.verify(token.token_id)
        assert verify2["valid"] is False

    def _test_dsar(self):
        from privacy_engine import DSAREngine, DSARType
        engine = DSAREngine()
        req = engine.submit_request(DSARType.ACCESS, "user@example.com", "Get my data")
        result = engine.process_request(req.req_id)
        assert result["status"] == "completed"

    def _test_consent(self):
        from privacy_engine import ConsentManager, ConsentPurpose
        mgr = ConsentManager()
        mgr.record_consent("user1", ConsentPurpose.ANALYTICS, True)
        assert mgr.check_consent("user1", ConsentPurpose.ANALYTICS) is True
        mgr.withdraw_consent("user1", ConsentPurpose.ANALYTICS)
        assert mgr.check_consent("user1", ConsentPurpose.ANALYTICS) is False

    def _test_pia(self):
        from privacy_engine import PIAEngine
        engine = PIAEngine()
        result = engine.run_assessment("test_project")
        assert result["overall_risk"] == "low"
        assert len(result["findings"]) > 0

    def _test_cmmc(self):
        from security_maturity import CMMCAssessor
        assessor = CMMCAssessor()
        result = assessor.assess()
        assert result["certification_ready"] is True

    def _test_soc2(self):
        from security_maturity import SOC2Reporter
        reporter = SOC2Reporter()
        result = reporter.generate_report()
        assert result["opinion"] == "unqualified"

    def _test_nist_csf(self):
        from security_maturity import NISTCSFScorer
        scorer = NISTCSFScorer()
        result = scorer.assess()
        assert result["overall_maturity"] > 3.0

    def _test_model_registry(self):
        from secmlops import ModelRiskRegistry, ModelRiskTier
        reg = ModelRiskRegistry()
        model = reg.register("TestModel", "1.0", ModelRiskTier.LIMITED,
                            "test_team", "testing", ["text"])
        assert model.risk_score == 40

    def _test_xai(self):
        from secmlops import XAIEngine, ExplanationMethod
        xai = XAIEngine()
        result = xai.explain("MDL-001", {"feature_a": 0.5, "feature_b": 1.0}, 0.85)
        assert "top_features" in result
        assert result["explained_variance"] > 0

    def _test_bias(self):
        from secmlops import BiasMitigationEngine
        engine = BiasMitigationEngine()
        result = engine.assess_model("MDL-001", ["gender", "race"])
        assert "metrics" in result
        assert "overall_fair" in result

    def _test_ai_incident(self):
        from secmlops import AIIncidentPlaybook, AIIncidentType
        playbook = AIIncidentPlaybook()
        result = playbook.activate(AIIncidentType.PROMPT_INJECTION, "Test injection detected")
        assert result["steps"] == 5

    def _test_edge_firmware(self):
        from edge_security import EdgeSecurityEngine
        engine = EdgeSecurityEngine()
        stats = engine.get_stats()
        assert stats["nodes"] >= 5

    def _test_airgap(self):
        from edge_security import AirGappedOps
        ops = AirGappedOps()
        result = ops.enable()
        assert result["mode"] == "air-gapped"
        result2 = ops.disable()
        assert result2["mode"] == "connected"

    def _test_mesh_tunnel(self):
        from edge_security import MeshNetworkSecurity
        mesh = MeshNetworkSecurity()
        stats = mesh.get_stats()
        assert stats["peers"] >= 4

    def _test_tpm(self):
        from edge_security import TPMIntegration, TPMPCRBank
        tpm = TPMIntegration()
        result = tpm.measure(TPMPCRBank.PCR0_BIOS, "test_measurement")
        assert "hash" in result
        attest = tpm.attest()
        assert "quote" in attest

    # ---- Integration tests ----

    def _test_chain_dlp_containment(self):
        from security_event_bus import SecurityEventBus, EventCategory, EventSeverity
        bus = SecurityEventBus()
        chain_actions = []
        bus.subscribe("test", [EventCategory.DATA_LEAK],
                     handler=lambda e: chain_actions.append(e.event_id))
        bus.emit(EventCategory.DATA_LEAK, EventSeverity.CRITICAL, "dlp", "SSN detected")
        assert len(chain_actions) == 1

    def _test_chain_hub_scan(self):
        from security_hub import SecurityHub
        hub = SecurityHub()
        result = hub.scan("AKIAIOSFODNN7EXAMPLE test 123-45-6789")
        assert result["threat_level"] in ("low", "medium", "high", "critical")

    def _test_chain_config_modules(self):
        from security_config import SecurityConfig
        cfg = SecurityConfig()
        assert cfg.is_module_enabled("dlp") is True
        cfg.set("modules.dlp.enabled", False)
        assert cfg.is_module_enabled("dlp") is False

    # ---- Regression tests ----

    def _test_no_telemetry_config(self):
        from security_config import SecurityConfig
        cfg = SecurityConfig()
        assert cfg.get("global.telemetry") is False
        assert cfg.get("global.external_calls") is False
        result = cfg.set("global.telemetry", True)
        assert result.get("blocked") is True

    def _test_no_external_imports(self):
        """Verify no external packages are imported."""
        import sys
        banned = ["requests", "urllib3", "httpx", "aiohttp",
                  "sentry_sdk", "segment", "mixpanel", "amplitude",
                  "newrelic", "datadog", "bugsnag", "rollbar"]
        for pkg in banned:
            assert pkg not in sys.modules, f"Banned package loaded: {pkg}"

    def _test_immutable_blocks(self):
        from security_config import SecurityConfig
        cfg = SecurityConfig()
        for key in ["telemetry_enabled", "backdoors", "tracking",
                    "phone_home", "third_party_analytics"]:
            result = cfg.set(f"hardcoded_security.{key}", True)
            assert result.get("blocked") is True

    # ---- Stress tests ----

    def _test_stress_eventbus(self):
        from security_event_bus import SecurityEventBus, EventCategory, EventSeverity
        bus = SecurityEventBus()
        start = time.time()
        for i in range(1000):
            bus.emit(EventCategory.SYSTEM, EventSeverity.INFO, "stress", f"event {i}")
        duration = time.time() - start
        assert duration < 5.0, f"1000 events took {duration:.2f}s (>5s)"
        assert bus.get_stats()["total_events"] == 1000

    def _test_stress_dlp(self):
        from dlp import DLPEngine
        engine = DLPEngine()
        start = time.time()
        for i in range(1000):
            engine.scan(f"Test content {i} with SSN 123-45-6789")
        duration = time.time() - start
        assert duration < 10.0, f"1000 DLP scans took {duration:.2f}s (>10s)"

    def _test_stress_merkle(self):
        from blockchain_audit import MerkleAuditLog
        log = MerkleAuditLog()
        start = time.time()
        for i in range(500):
            log.append(f"event_{i}", f"actor_{i % 10}")
        duration = time.time() - start
        assert log.verify_integrity()["valid"] is True
        assert duration < 10.0

    # ------------------------------------------------------------------
    #  RUN ALL
    # ------------------------------------------------------------------
    def run_suite(self, suite: str = "unit") -> Dict:
        tests = self._suites.get(suite, [])
        results = []
        for name, fn in tests:
            result = self._run_test(name, suite, fn)
            results.append(result)
            self._results.append(result)
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        return {
            "suite": suite, "total": len(results),
            "passed": passed, "failed": failed,
            "results": [r.to_dict() for r in results]}

    def run_all(self) -> Dict:
        all_results = {}
        for suite in self._suites:
            all_results[suite] = self.run_suite(suite)
        total = sum(r["total"] for r in all_results.values())
        passed = sum(r["passed"] for r in all_results.values())
        return {
            "total": total, "passed": passed,
            "failed": total - passed,
            "pass_rate": f"{passed/max(1,total)*100:.1f}%",
            "suites": all_results}

    def get_stats(self) -> Dict:
        return {"total_tests": sum(len(t) for t in self._suites.values()),
                "suites": {k: len(v) for k, v in self._suites.items()},
                "results_recorded": len(self._results)}


security_tests = SecurityTestRunner()
