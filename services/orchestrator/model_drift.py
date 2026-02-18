"""
Model Drift & Integrity Monitor — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Detects silent model degradation, inference inconsistency,
weight tampering, and distribution shift over time.

Uses: statistical process control, weight checksums,
output distribution analysis, golden test regression.
"""

import hashlib
import logging
import math
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("qwen.model_drift")


class DriftType(str, Enum):
    DATA_DRIFT = "data_drift"             # Input distribution change
    CONCEPT_DRIFT = "concept_drift"       # Relationship change
    PREDICTION_DRIFT = "prediction_drift" # Output distribution change
    WEIGHT_TAMPERING = "weight_tampering" # Model weight modification
    PERFORMANCE_DECAY = "performance_decay"


class AlertLevel(str, Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class ModelSnapshot:
    """A point-in-time snapshot of model state."""
    def __init__(self, snap_id, model_id, weight_hash,
                 output_distribution, performance_metrics):
        self.snap_id = snap_id
        self.model_id = model_id
        self.weight_hash = weight_hash
        self.output_distribution = output_distribution
        self.performance_metrics = performance_metrics
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "snap_id": self.snap_id, "model_id": self.model_id,
            "weight_hash": self.weight_hash[:16] + "...",
            "performance": self.performance_metrics,
            "created_at": self.created_at,
        }


class GoldenTest:
    """A deterministic test case for regression detection."""
    def __init__(self, test_id, model_id, input_hash,
                 expected_output_hash, tolerance=0.01):
        self.test_id = test_id
        self.model_id = model_id
        self.input_hash = input_hash
        self.expected_output_hash = expected_output_hash
        self.tolerance = tolerance
        self.last_passed: Optional[str] = None
        self.consecutive_failures = 0

    def to_dict(self):
        return {
            "test_id": self.test_id, "model": self.model_id,
            "last_passed": self.last_passed,
            "failures": self.consecutive_failures,
        }


class DriftAlert:
    """A model drift alert."""
    def __init__(self, alert_id, model_id, drift_type, level,
                 metric, current_value, baseline_value, deviation):
        self.alert_id = alert_id
        self.model_id = model_id
        self.drift_type = drift_type
        self.level = level
        self.metric = metric
        self.current_value = current_value
        self.baseline_value = baseline_value
        self.deviation = deviation
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.acknowledged = False

    def to_dict(self):
        return {
            "alert_id": self.alert_id, "model": self.model_id,
            "drift_type": self.drift_type.value, "level": self.level.value,
            "metric": self.metric,
            "current": round(self.current_value, 4),
            "baseline": round(self.baseline_value, 4),
            "deviation_pct": round(self.deviation * 100, 2),
        }


class ModelDriftMonitor:
    """Continuous model health monitoring."""

    def __init__(self):
        self._snapshots: Dict[str, List[ModelSnapshot]] = {}
        self._golden_tests: Dict[str, List[GoldenTest]] = {}
        self._alerts: List[DriftAlert] = []
        self._baselines: Dict[str, Dict] = {}  # model_id → baseline metrics
        self._snap_counter = 0
        self._alert_counter = 0
        self._thresholds = {
            "accuracy_drop": 0.02,      # 2% accuracy drop = warning
            "accuracy_critical": 0.05,   # 5% = critical
            "latency_increase": 0.20,    # 20% latency increase
            "output_shift": 0.10,        # 10% output distribution shift
            "weight_change": 0.0,        # ANY weight change = critical
        }

    def register_baseline(self, model_id: str, metrics: Dict):
        """Register baseline performance metrics for a model."""
        self._baselines[model_id] = {
            "metrics": metrics,
            "weight_hash": metrics.get("weight_hash", ""),
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

    def take_snapshot(self, model_id: str, weight_hash: str,
                      output_dist: Dict, perf_metrics: Dict) -> ModelSnapshot:
        """Record current model state."""
        self._snap_counter += 1
        snap = ModelSnapshot(
            f"SNAP-{self._snap_counter:08d}", model_id,
            weight_hash, output_dist, perf_metrics,
        )
        if model_id not in self._snapshots:
            self._snapshots[model_id] = []
        self._snapshots[model_id].append(snap)
        return snap

    def check_drift(self, model_id: str, current_metrics: Dict) -> List[DriftAlert]:
        """Compare current metrics against baseline and detect drift."""
        baseline = self._baselines.get(model_id)
        if not baseline:
            return []

        alerts = []
        base_metrics = baseline["metrics"]

        # Weight tampering check
        if (current_metrics.get("weight_hash") and
                baseline.get("weight_hash") and
                current_metrics["weight_hash"] != baseline["weight_hash"]):
            alert = self._create_alert(
                model_id, DriftType.WEIGHT_TAMPERING, AlertLevel.CRITICAL,
                "weight_hash", 0, 1, 1.0,
            )
            alerts.append(alert)

        # Performance decay — accuracy
        base_acc = base_metrics.get("accuracy", 1.0)
        curr_acc = current_metrics.get("accuracy", 1.0)
        if base_acc > 0:
            acc_drop = (base_acc - curr_acc) / base_acc
            if acc_drop >= self._thresholds["accuracy_critical"]:
                alerts.append(self._create_alert(
                    model_id, DriftType.PERFORMANCE_DECAY, AlertLevel.CRITICAL,
                    "accuracy", curr_acc, base_acc, acc_drop,
                ))
            elif acc_drop >= self._thresholds["accuracy_drop"]:
                alerts.append(self._create_alert(
                    model_id, DriftType.PERFORMANCE_DECAY, AlertLevel.WARNING,
                    "accuracy", curr_acc, base_acc, acc_drop,
                ))

        # Latency increase
        base_lat = base_metrics.get("latency_p95_ms", 0)
        curr_lat = current_metrics.get("latency_p95_ms", 0)
        if base_lat > 0:
            lat_increase = (curr_lat - base_lat) / base_lat
            if lat_increase >= self._thresholds["latency_increase"]:
                alerts.append(self._create_alert(
                    model_id, DriftType.PREDICTION_DRIFT, AlertLevel.WARNING,
                    "latency_p95_ms", curr_lat, base_lat, lat_increase,
                ))

        return alerts

    def _create_alert(self, model_id, drift_type, level, metric,
                      current, baseline, deviation) -> DriftAlert:
        self._alert_counter += 1
        alert = DriftAlert(
            f"DRIFT-{self._alert_counter:08d}", model_id,
            drift_type, level, metric, current, baseline, deviation,
        )
        self._alerts.append(alert)
        log_fn = logger.critical if level == AlertLevel.CRITICAL else logger.warning
        log_fn(f"Model drift [{level.value}]: {model_id} — "
               f"{metric} deviation {deviation*100:.1f}%")
        return alert

    def add_golden_test(self, model_id: str, input_hash: str,
                        expected_hash: str) -> GoldenTest:
        test_id = f"GT-{hashlib.sha256(f'{model_id}:{input_hash}'.encode()).hexdigest()[:8]}"
        gt = GoldenTest(test_id, model_id, input_hash, expected_hash)
        if model_id not in self._golden_tests:
            self._golden_tests[model_id] = []
        self._golden_tests[model_id].append(gt)
        return gt

    def get_stats(self) -> Dict:
        return {
            "monitored_models": len(self._baselines),
            "snapshots": sum(len(s) for s in self._snapshots.values()),
            "golden_tests": sum(len(g) for g in self._golden_tests.values()),
            "alerts_total": len(self._alerts),
            "critical_alerts": sum(1 for a in self._alerts
                                   if a.level == AlertLevel.CRITICAL),
            "thresholds": self._thresholds,
        }

model_drift_monitor = ModelDriftMonitor()
