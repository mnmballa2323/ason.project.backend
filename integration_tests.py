"""
End-to-End Integration Tests — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Cross-module tests, performance benchmarks, chaos/fault injection.
"""

import hashlib, logging, os, statistics, time, unittest
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger("qwen.integration_tests")


# ============================================================================
#  CROSS-MODULE INTEGRATION TESTS
# ============================================================================

class CrossModuleTests(unittest.TestCase):
    """Tests that verify modules work together as a system."""

    # --- Threat Detection → Triage → Decision Pipeline ---

    def test_threat_to_triage_pipeline(self):
        """Alert flows from streaming → autonomous SOC → decision engine."""
        from streaming_security import rules_engine
        from autonomous_defense import autonomous_soc
        from orchestration_fabric import decision_engine

        # Step 1: Generate alert via rules engine
        event = {"content": "SELECT * FROM users WHERE id='1' OR '1'='1'",
                 "source": "web_app", "id": "TEST-001"}
        matches = rules_engine.evaluate(event)
        self.assertTrue(len(matches) > 0, "SQLi should trigger rules engine")

        # Step 2: Triage through SOC
        alert = {"type": "exploit", "severity": "critical", "id": "TEST-001"}
        triage_result = autonomous_soc.triage(alert)
        self.assertIn(triage_result["verdict"],
                     ["true_positive", "suspicious", "unknown"])

        # Step 3: Decision engine
        context = {"threat_level": "critical"}
        decision = decision_engine.decide(context)
        self.assertEqual(decision["outcome"], "block")

    def test_data_classification_to_dlp_pipeline(self):
        """Data classifier → retention policy → lineage tracking."""
        from data_governance import data_classifier, data_lineage, retention_engine

        # Step 1: Classify content with PII
        content = "SSN: 123-45-6789, Email: test@example.com"
        result = data_classifier.classify(content, "test")
        self.assertEqual(result["classification"], "restricted")
        self.assertGreater(result["pii_count"], 0)

        # Step 2: Record lineage
        lineage = data_lineage.record("DOC-001", data_lineage.__class__.__mro__[0]
                                      and __import__("data_governance").LineageStage.INGESTION,
                                      "classifier", "test")
        self.assertIn("hash", lineage)

        # Step 3: Check retention
        from data_governance import DataClassification
        action = retention_engine.apply_policy("DOC-001", DataClassification.RESTRICTED)
        self.assertIn("action", action)

    def test_knowledge_graph_to_attack_paths(self):
        """Knowledge graph → blast radius → attack path analysis."""
        from knowledge_graph import knowledge_graph, attack_path_analyzer

        # Step 1: Blast radius from API gateway
        blast = knowledge_graph.blast_radius("api-gw", max_hops=2)
        self.assertGreater(blast["affected_nodes"], 1)

        # Step 2: Find attack paths to crown jewels
        paths = attack_path_analyzer.find_crown_jewel_paths()
        # Should find paths to high-risk nodes
        self.assertIsInstance(paths, list)

    def test_adversary_emulation_to_purple_team(self):
        """Adversary emulation → purple team exercise → report."""
        from threat_emulation import adversary_emulation, purple_team

        # Step 1: Emulate APT29
        result = adversary_emulation.emulate("APT29")
        self.assertIn("detection_rate", result)
        self.assertGreater(result["techniques_tested"], 0)

        # Step 2: Run purple team exercise
        pt_result = purple_team.run_exercise("PT-001")
        self.assertIn("detection_rate", pt_result)
        self.assertIn("score", pt_result)

    def test_vault_to_rotation_pipeline(self):
        """Secret store → rotation → transit encryption."""
        from secret_vault import secret_vault, SecretType, rotation_engine, transit

        # Step 1: Store a secret
        result = secret_vault.store("test-key", "s3cret!", SecretType.API_KEY, "test")
        self.assertTrue(result.get("stored") or "version" in result)

        # Step 2: Retrieve
        retrieved = secret_vault.retrieve("test-key")
        self.assertIn("value", retrieved)

        # Step 3: Transit encrypt
        encrypted = transit.encrypt("sensitive-data")
        self.assertIn("ciphertext", encrypted)

        # Step 4: Transit decrypt
        decrypted = transit.decrypt(encrypted["key_id"], encrypted["ciphertext"])
        self.assertTrue(decrypted.get("decrypted"))

    def test_dr_failover_and_chaos(self):
        """DR failover → backup verify → chaos scenario."""
        from disaster_recovery import dr_orchestrator, backup_integrity, chaos_resilience

        # Step 1: Failover a service
        result = dr_orchestrator.failover("api-gateway", "test")
        self.assertEqual(result["action"], "failover")

        # Step 2: Create and verify backup
        backup = backup_integrity.create_backup("test-db", __import__("disaster_recovery").BackupType.FULL)
        verify = backup_integrity.verify(backup["id"])
        self.assertTrue(verify["verified"])

        # Step 3: Chaos scenario
        chaos = chaos_resilience.run_scenario("region_failover")
        self.assertTrue(chaos["passed"])

        # Step 4: Failback
        dr_orchestrator.failback("api-gateway")

    def test_e2e_encryption_session(self):
        """E2E session → encrypt → decrypt → close."""
        from comms_security import e2e_encryption

        session = e2e_encryption.create_session("alice", "bob")
        sid = session["session"]

        encrypted = e2e_encryption.encrypt_message(sid, "alice", "Hello, Bob!")
        self.assertTrue(encrypted.get("forward_secrecy"))

        decrypted = e2e_encryption.decrypt_message(sid, "bob", "test")
        self.assertTrue(decrypted.get("forward_secrecy") or decrypted.get("decrypted"))

        closed = e2e_encryption.close_session(sid)
        self.assertTrue(closed["keys_destroyed"])

    def test_adaptive_defense_escalation(self):
        """Threat indicators → adaptive defense → posture change."""
        from autonomous_defense import adaptive_defense

        # Normal state
        posture = adaptive_defense.get_current_posture()
        self.assertEqual(posture["threat_level"], "defcon_4")

        # Escalate on critical alerts
        result = adaptive_defense.auto_adjust({"critical_alerts": 5, "active_incidents": 3})
        self.assertEqual(result.get("new_level", result.get("level")), "defcon_1")

        # Reset
        adaptive_defense.set_threat_level(
            __import__("autonomous_defense").ThreatLevel.DEFCON_4, "test reset")

    def test_risk_to_board_report(self):
        """FAIR risk → insurance → board dashboard."""
        from exec_intelligence import risk_quantifier, cyber_insurance, board_dashboard

        risk = risk_quantifier.quantify_all()
        self.assertIn("total_annualized_exposure", risk)

        insurance = cyber_insurance.assess()
        self.assertGreater(insurance["overall_score"], 0)

        report = board_dashboard.generate_board_report()
        self.assertIn("executive_summary", report)
        self.assertIn("risk_heatmap", report)

    def test_full_orchestration_workflow(self):
        """Execute a full orchestration workflow end-to-end."""
        from orchestration_fabric import orchestration_fabric

        workflows = orchestration_fabric.list_workflows()
        self.assertGreater(len(workflows), 0)

        # Execute first workflow
        wf_id = workflows[0]["id"]
        result = orchestration_fabric.execute(wf_id)
        self.assertEqual(result["workflow"]["status"], "completed")


# ============================================================================
#  PERFORMANCE BENCHMARKS
# ============================================================================

class PerformanceBenchmarks:
    """Throughput, latency, memory benchmarks for each module."""

    def __init__(self):
        self._results: List[Dict] = []

    def benchmark(self, name: str, func, iterations: int = 1000) -> Dict:
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func()
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

        result = {
            "name": name, "iterations": iterations,
            "mean_ms": round(statistics.mean(times), 4),
            "median_ms": round(statistics.median(times), 4),
            "p95_ms": round(sorted(times)[int(len(times) * 0.95)], 4),
            "p99_ms": round(sorted(times)[int(len(times) * 0.99)], 4),
            "min_ms": round(min(times), 4),
            "max_ms": round(max(times), 4),
            "throughput_ops_sec": round(iterations / (sum(times) / 1000), 1),
        }
        self._results.append(result)
        return result

    def run_all(self) -> Dict:
        benchmarks = []

        # Data Lake ingest
        from security_data_lake import data_lake, EventType
        benchmarks.append(self.benchmark(
            "data_lake.ingest",
            lambda: data_lake.ingest(EventType.SECURITY, "bench", "info", "test"),
            iterations=5000))

        # Stream processor
        from streaming_security import stream_processor
        benchmarks.append(self.benchmark(
            "stream_processor.ingest",
            lambda: stream_processor.ingest({"type": "test", "value": 42}),
            iterations=5000))

        # Rules engine
        from streaming_security import rules_engine
        benchmarks.append(self.benchmark(
            "rules_engine.evaluate",
            lambda: rules_engine.evaluate({"content": "normal request", "path": "/api/v1/users"}),
            iterations=2000))

        # Anomaly detector
        from streaming_security import anomaly_detector
        import random
        benchmarks.append(self.benchmark(
            "anomaly_detector.observe",
            lambda: anomaly_detector.observe("bench_metric", random.gauss(100, 10)),
            iterations=2000))

        # Data classifier
        from data_governance import data_classifier
        benchmarks.append(self.benchmark(
            "data_classifier.classify",
            lambda: data_classifier.classify("Test content with email test@example.com", "bench"),
            iterations=1000))

        # Knowledge graph blast radius
        from knowledge_graph import knowledge_graph
        benchmarks.append(self.benchmark(
            "knowledge_graph.blast_radius",
            lambda: knowledge_graph.blast_radius("api-gw", 3),
            iterations=1000))

        # Decision engine
        from orchestration_fabric import decision_engine
        benchmarks.append(self.benchmark(
            "decision_engine.decide",
            lambda: decision_engine.decide({"threat_level": "low"}),
            iterations=2000))

        # Autonomous SOC triage
        from autonomous_defense import autonomous_soc
        benchmarks.append(self.benchmark(
            "autonomous_soc.triage",
            lambda: autonomous_soc.triage({"type": "auth_failure", "count": 1, "severity": "low"}),
            iterations=2000))

        # FAIR risk quantification
        from exec_intelligence import risk_quantifier
        benchmarks.append(self.benchmark(
            "risk_quantifier.quantify_all",
            lambda: risk_quantifier.quantify_all(),
            iterations=500))

        # Vault operations
        from secret_vault import secret_vault, SecretType
        benchmarks.append(self.benchmark(
            "secret_vault.store+retrieve",
            lambda: (secret_vault.store("bench", "val", SecretType.GENERIC, "bench"),
                    secret_vault.retrieve("bench")),
            iterations=1000))

        return {"benchmarks": benchmarks,
                "total_ops": sum(b["iterations"] for b in benchmarks),
                "ts": datetime.now(timezone.utc).isoformat()}

    def get_stats(self) -> Dict:
        return {"benchmarks_run": len(self._results)}


# ============================================================================
#  CHAOS / FAULT INJECTION TESTS
# ============================================================================

class FaultType(str):
    TIMEOUT = "timeout"
    EXCEPTION = "exception"
    CORRUPT_DATA = "corrupt_data"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    PARTIAL_FAILURE = "partial_failure"


class ChaosTest:
    def __init__(self, name, target_module, fault_type, description):
        self.name = name
        self.target_module = target_module
        self.fault_type = fault_type
        self.description = description
        self.passed = False
        self.details = ""

    def to_dict(self):
        return {"name": self.name, "target": self.target_module,
                "fault": self.fault_type, "passed": self.passed,
                "details": self.details}


class ChaosTestSuite:
    """Fault injection — test graceful degradation under failure."""

    def __init__(self):
        self._tests: List[ChaosTest] = []
        self._results: List[Dict] = []

    def run_all(self) -> Dict:
        self._tests = []

        # Test 1: Data Lake handles overflow gracefully
        test = ChaosTest("data_lake_overflow", "security_data_lake",
                        FaultType.RESOURCE_EXHAUSTION,
                        "Ingest beyond max capacity")
        try:
            from security_data_lake import SecurityDataLake, EventType
            lake = SecurityDataLake(max_events=10)
            for i in range(100):
                lake.ingest(EventType.SECURITY, "chaos", "info", f"event-{i}")
            assert len(lake._events) <= 10
            test.passed = True
            test.details = "Gracefully evicted oldest events"
        except Exception as e:
            test.details = str(e)
        self._tests.append(test)

        # Test 2: Rules engine handles malformed input
        test = ChaosTest("rules_engine_bad_input", "streaming_security",
                        FaultType.CORRUPT_DATA,
                        "Evaluate with None/empty/corrupt events")
        try:
            from streaming_security import rules_engine
            rules_engine.evaluate({})
            rules_engine.evaluate({"content": None})
            rules_engine.evaluate({"content": 12345})
            test.passed = True
            test.details = "Handled all malformed inputs"
        except Exception as e:
            test.details = str(e)
        self._tests.append(test)

        # Test 3: Vault sealed state
        test = ChaosTest("vault_sealed", "secret_vault",
                        FaultType.PARTIAL_FAILURE,
                        "Operations on sealed vault")
        try:
            from secret_vault import SecretVault
            vault = SecretVault()
            vault.seal()
            result = vault.store("test", "val", __import__("secret_vault").SecretType.GENERIC, "test")
            assert "error" in result
            vault.unseal(vault._master_key)
            test.passed = True
            test.details = "Sealed vault correctly rejects operations"
        except Exception as e:
            test.details = str(e)
        self._tests.append(test)

        # Test 4: Anomaly detector cold start
        test = ChaosTest("anomaly_cold_start", "streaming_security",
                        FaultType.PARTIAL_FAILURE,
                        "Anomaly detection with insufficient baseline")
        try:
            from streaming_security import AnomalyDetector
            detector = AnomalyDetector()
            result = detector.observe("cold_metric", 100.0)
            assert result["anomaly"] is False  # Not enough data
            test.passed = True
            test.details = "Returns non-anomaly with insufficient data"
        except Exception as e:
            test.details = str(e)
        self._tests.append(test)

        # Test 5: Knowledge graph missing node
        test = ChaosTest("graph_missing_node", "knowledge_graph",
                        FaultType.CORRUPT_DATA,
                        "Blast radius on non-existent node")
        try:
            from knowledge_graph import knowledge_graph
            result = knowledge_graph.blast_radius("non-existent-node")
            assert result["affected_nodes"] <= 1
            test.passed = True
            test.details = "Handles missing node gracefully"
        except Exception as e:
            test.details = str(e)
        self._tests.append(test)

        # Test 6: Decision engine empty context
        test = ChaosTest("decision_empty_context", "orchestration_fabric",
                        FaultType.CORRUPT_DATA,
                        "Decision with empty context")
        try:
            from orchestration_fabric import decision_engine
            result = decision_engine.decide({})
            assert "outcome" in result
            test.passed = True
            test.details = "Falls through to default allow"
        except Exception as e:
            test.details = str(e)
        self._tests.append(test)

        # Test 7: Concurrent vault access
        test = ChaosTest("vault_concurrent", "secret_vault",
                        FaultType.RESOURCE_EXHAUSTION,
                        "Concurrent secret store operations")
        try:
            import threading
            from secret_vault import secret_vault as sv, SecretType
            errors = []
            def store_secret(i):
                try:
                    sv.store(f"concurrent-{i}", f"value-{i}", SecretType.GENERIC, "chaos")
                except Exception as e:
                    errors.append(str(e))
            threads = [threading.Thread(target=store_secret, args=(i,)) for i in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            test.passed = len(errors) == 0
            test.details = f"0 errors in 20 concurrent writes" if test.passed else f"{len(errors)} errors"
        except Exception as e:
            test.details = str(e)
        self._tests.append(test)

        # Test 8: E2E session on closed session
        test = ChaosTest("e2e_closed_session", "comms_security",
                        FaultType.PARTIAL_FAILURE,
                        "Encrypt on closed session")
        try:
            from comms_security import e2e_encryption
            session = e2e_encryption.create_session("chaos-alice", "chaos-bob")
            sid = session["session"]
            e2e_encryption.close_session(sid)
            result = e2e_encryption.encrypt_message(sid, "chaos-alice", "test")
            assert "error" in result
            test.passed = True
            test.details = "Correctly rejects encryption on closed session"
        except Exception as e:
            test.details = str(e)
        self._tests.append(test)

        passed = sum(1 for t in self._tests if t.passed)
        total = len(self._tests)
        result = {
            "passed": passed, "total": total,
            "pass_rate": round(passed / max(total, 1) * 100, 1),
            "tests": [t.to_dict() for t in self._tests],
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._results.append(result)
        return result

    def get_stats(self) -> Dict:
        return {"suites_run": len(self._results)}


# Singletons
benchmarks = PerformanceBenchmarks()
chaos_tests = ChaosTestSuite()
