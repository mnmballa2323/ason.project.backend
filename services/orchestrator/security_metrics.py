"""
Security Metrics Engine — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Prometheus-style counters, gauges, histograms for all security modules.
"""

import logging, math, threading, time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.metrics")


class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class Metric:
    def __init__(self, name: str, metric_type: MetricType,
                 description: str, labels: Dict[str, str] = None):
        self.name = name
        self.type = metric_type
        self.description = description
        self.labels = labels or {}
        self.value = 0.0
        self._observations: List[float] = []
        self._lock = threading.Lock()

    def inc(self, amount: float = 1.0):
        with self._lock:
            self.value += amount

    def dec(self, amount: float = 1.0):
        with self._lock:
            self.value -= amount

    def set_value(self, val: float):
        with self._lock:
            self.value = val

    def observe(self, val: float):
        with self._lock:
            self._observations.append(val)
            self.value = val

    def histogram_stats(self) -> Dict:
        if not self._observations:
            return {"count": 0}
        obs = sorted(self._observations)
        return {
            "count": len(obs),
            "min": round(obs[0], 4),
            "max": round(obs[-1], 4),
            "mean": round(sum(obs) / len(obs), 4),
            "p50": round(obs[len(obs) // 2], 4),
            "p95": round(obs[int(len(obs) * 0.95)], 4),
            "p99": round(obs[int(len(obs) * 0.99)], 4),
        }

    def to_dict(self) -> Dict:
        result = {"name": self.name, "type": self.type.value,
                  "value": round(self.value, 4), "labels": self.labels}
        if self.type == MetricType.HISTOGRAM:
            result["histogram"] = self.histogram_stats()
        return result


class SecurityMetricsEngine:
    """Self-hosted Prometheus-style metrics for all security modules."""

    def __init__(self):
        self._metrics: Dict[str, Metric] = {}
        self._lock = threading.Lock()
        self._seed()

    def _seed(self):
        # Pre-register core security metrics
        metrics = [
            ("security_events_total", MetricType.COUNTER, "Total security events"),
            ("threats_detected_total", MetricType.COUNTER, "Threats detected"),
            ("threats_blocked_total", MetricType.COUNTER, "Threats blocked"),
            ("dlp_findings_total", MetricType.COUNTER, "DLP findings"),
            ("auth_failures_total", MetricType.COUNTER, "Auth failures"),
            ("containment_actions_total", MetricType.COUNTER, "Containment actions"),
            ("soar_playbooks_triggered", MetricType.COUNTER, "SOAR playbooks"),
            ("compliance_score", MetricType.GAUGE, "Compliance score %"),
            ("posture_score", MetricType.GAUGE, "Security posture score"),
            ("mttr_seconds", MetricType.HISTOGRAM, "Mean time to respond"),
            ("scan_duration_ms", MetricType.HISTOGRAM, "Scan duration"),
            ("modules_active", MetricType.GAUGE, "Active security modules"),
            ("event_bus_queue_depth", MetricType.GAUGE, "Event bus queue depth"),
            ("encryption_operations", MetricType.COUNTER, "Crypto operations"),
            ("audit_log_entries", MetricType.COUNTER, "Audit log entries"),
        ]
        for name, mtype, desc in metrics:
            self._metrics[name] = Metric(name, mtype, desc)

    def counter(self, name: str, description: str = "") -> Metric:
        if name not in self._metrics:
            self._metrics[name] = Metric(name, MetricType.COUNTER, description)
        return self._metrics[name]

    def gauge(self, name: str, description: str = "") -> Metric:
        if name not in self._metrics:
            self._metrics[name] = Metric(name, MetricType.GAUGE, description)
        return self._metrics[name]

    def histogram(self, name: str, description: str = "") -> Metric:
        if name not in self._metrics:
            self._metrics[name] = Metric(name, MetricType.HISTOGRAM, description)
        return self._metrics[name]

    def export(self) -> Dict:
        """Export all metrics in Prometheus format."""
        return {name: m.to_dict() for name, m in self._metrics.items()}

    def export_prometheus_text(self) -> str:
        """Export in Prometheus text exposition format."""
        lines = []
        for name, m in self._metrics.items():
            lines.append(f"# HELP {name} {m.description}")
            lines.append(f"# TYPE {name} {m.type.value}")
            labels = ",".join(f'{k}="{v}"' for k, v in m.labels.items())
            label_str = f"{{{labels}}}" if labels else ""
            lines.append(f"{name}{label_str} {m.value}")
        return "\n".join(lines)

    def get_stats(self) -> Dict:
        return {"metrics_registered": len(self._metrics),
                "counters": sum(1 for m in self._metrics.values() if m.type == MetricType.COUNTER),
                "gauges": sum(1 for m in self._metrics.values() if m.type == MetricType.GAUGE),
                "histograms": sum(1 for m in self._metrics.values() if m.type == MetricType.HISTOGRAM)}


security_metrics = SecurityMetricsEngine()
