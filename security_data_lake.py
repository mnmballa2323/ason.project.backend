"""
Security Data Lake & Analytics — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Centralized event storage, SQL-like querying, threat analytics,
KPI tracking (MTTD/MTTR), SIEM-style log correlation.
"""

import hashlib, logging, math, re, statistics, threading, time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("qwen.data_lake")


# ============================================================================
#  SECURITY DATA LAKE
# ============================================================================

class EventType(str, Enum):
    THREAT = "threat"
    AUTH = "auth"
    ACCESS = "access"
    DLP = "dlp"
    COMPLIANCE = "compliance"
    SYSTEM = "system"
    NETWORK = "network"
    AUDIT = "audit"


class DataLakeEvent:
    __slots__ = ("event_id", "event_type", "source", "severity",
                 "message", "data", "timestamp", "tags", "indexed")

    def __init__(self, event_id, event_type, source, severity,
                 message, data=None, tags=None):
        self.event_id = event_id
        self.event_type = event_type
        self.source = source
        self.severity = severity
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc)
        self.tags = tags or []
        self.indexed = True

    def to_dict(self):
        return {
            "id": self.event_id, "type": self.event_type.value,
            "source": self.source, "severity": self.severity,
            "message": self.message[:120], "ts": self.timestamp.isoformat(),
            "tags": self.tags,
        }


class SecurityDataLake:
    """In-memory security data lake with SQL-like query."""

    def __init__(self, max_events: int = 100000):
        self._events: List[DataLakeEvent] = []
        self._indexes: Dict[str, Dict[str, List[int]]] = {
            "type": defaultdict(list),
            "source": defaultdict(list),
            "severity": defaultdict(list),
        }
        self._max = max_events
        self._counter = 0
        self._lock = threading.Lock()

    def ingest(self, event_type: EventType, source: str, severity: str,
               message: str, data: Dict = None, tags: List[str] = None) -> str:
        with self._lock:
            self._counter += 1
            eid = f"DL-{self._counter:012d}"
        event = DataLakeEvent(eid, event_type, source, severity, message, data, tags)
        idx = len(self._events)
        self._events.append(event)
        self._indexes["type"][event_type.value].append(idx)
        self._indexes["source"][source].append(idx)
        self._indexes["severity"][severity].append(idx)
        # Evict oldest if over limit
        if len(self._events) > self._max:
            self._events = self._events[-self._max:]
            self._rebuild_indexes()
        return eid

    def _rebuild_indexes(self):
        self._indexes = {"type": defaultdict(list), "source": defaultdict(list),
                         "severity": defaultdict(list)}
        for i, e in enumerate(self._events):
            self._indexes["type"][e.event_type.value].append(i)
            self._indexes["source"][e.source].append(i)
            self._indexes["severity"][e.severity].append(i)

    def query(self, where: Dict = None, order_by: str = "timestamp",
              desc: bool = True, limit: int = 50) -> List[Dict]:
        """SQL-like query: query(where={"type": "threat", "severity": "critical"})"""
        results = list(range(len(self._events)))
        if where:
            for field, value in where.items():
                if field in self._indexes:
                    indexed = set(self._indexes[field].get(value, []))
                    results = [r for r in results if r in indexed]
                else:
                    results = [r for r in results
                               if getattr(self._events[r], field, None) == value]
        events = [self._events[i] for i in results]
        events.sort(key=lambda e: e.timestamp, reverse=desc)
        return [e.to_dict() for e in events[:limit]]

    def count(self, where: Dict = None) -> int:
        if not where:
            return len(self._events)
        return len(self.query(where=where, limit=999999))

    def aggregate(self, group_by: str, metric: str = "count") -> Dict:
        groups = defaultdict(int)
        for e in self._events:
            key = getattr(e, group_by, "unknown")
            if isinstance(key, Enum):
                key = key.value
            groups[key] += 1
        return dict(sorted(groups.items(), key=lambda x: x[1], reverse=True))

    def get_stats(self) -> Dict:
        return {"total_events": len(self._events), "max_capacity": self._max,
                "indexes": {k: len(v) for k, v in self._indexes.items()}}


# ============================================================================
#  THREAT ANALYTICS
# ============================================================================

class ThreatAnalytics:
    """Statistical anomaly detection & trend analysis."""

    def __init__(self):
        self._baselines: Dict[str, List[float]] = defaultdict(list)
        self._anomalies: List[Dict] = []

    def record_metric(self, metric_name: str, value: float):
        self._baselines[metric_name].append(value)
        # Keep last 1000 observations
        if len(self._baselines[metric_name]) > 1000:
            self._baselines[metric_name] = self._baselines[metric_name][-1000:]

    def detect_anomalies(self, metric_name: str, current_value: float,
                        z_threshold: float = 3.0) -> Dict:
        baseline = self._baselines.get(metric_name, [])
        if len(baseline) < 10:
            return {"anomaly": False, "reason": "insufficient_data"}
        mean = statistics.mean(baseline)
        stdev = statistics.stdev(baseline) or 0.001
        z_score = (current_value - mean) / stdev
        is_anomaly = abs(z_score) > z_threshold
        result = {
            "metric": metric_name, "value": current_value,
            "mean": round(mean, 4), "stdev": round(stdev, 4),
            "z_score": round(z_score, 4), "anomaly": is_anomaly,
            "direction": "above" if z_score > 0 else "below",
        }
        if is_anomaly:
            self._anomalies.append(result)
        return result

    def trend_analysis(self, metric_name: str, window: int = 24) -> Dict:
        baseline = self._baselines.get(metric_name, [])
        if len(baseline) < window * 2:
            return {"trend": "insufficient_data"}
        prev = baseline[-window*2:-window]
        curr = baseline[-window:]
        prev_avg = statistics.mean(prev)
        curr_avg = statistics.mean(curr)
        change_pct = ((curr_avg - prev_avg) / max(prev_avg, 0.001)) * 100
        return {
            "metric": metric_name, "window": window,
            "previous_avg": round(prev_avg, 4), "current_avg": round(curr_avg, 4),
            "change_pct": round(change_pct, 2),
            "trend": "increasing" if change_pct > 10 else
                     "decreasing" if change_pct < -10 else "stable",
        }

    def predictive_score(self, metric_name: str) -> Dict:
        """Simple linear extrapolation for next-period prediction."""
        baseline = self._baselines.get(metric_name, [])
        if len(baseline) < 20:
            return {"prediction": None, "reason": "insufficient_data"}
        recent = baseline[-20:]
        x = list(range(len(recent)))
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(recent)
        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, recent))
        denominator = sum((xi - x_mean) ** 2 for xi in x) or 0.001
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        next_val = slope * (len(recent)) + intercept
        return {
            "metric": metric_name, "predicted_next": round(next_val, 4),
            "slope": round(slope, 4), "confidence": "low" if len(baseline) < 50 else "medium",
        }

    def get_stats(self) -> Dict:
        return {"metrics_tracked": len(self._baselines),
                "anomalies_detected": len(self._anomalies)}


# ============================================================================
#  KPI ENGINE
# ============================================================================

class SecurityKPIEngine:
    """Track MTTD, MTTR, false positive rate, coverage metrics."""

    def __init__(self):
        self._incidents: List[Dict] = []
        self._detections: List[Dict] = []
        self._kpi_history: Dict[str, List[float]] = defaultdict(list)

    def record_detection(self, threat_id: str, detected_at: float,
                        occurred_at: float):
        ttd = detected_at - occurred_at
        self._detections.append({"id": threat_id, "ttd": ttd})
        self._kpi_history["mttd"].append(ttd)

    def record_response(self, incident_id: str, detected_at: float,
                       resolved_at: float):
        ttr = resolved_at - detected_at
        self._incidents.append({"id": incident_id, "ttr": ttr})
        self._kpi_history["mttr"].append(ttr)

    def record_alert(self, is_true_positive: bool):
        self._kpi_history["precision"].append(1.0 if is_true_positive else 0.0)

    def get_kpis(self) -> Dict:
        mttd = self._kpi_history.get("mttd", [])
        mttr = self._kpi_history.get("mttr", [])
        precision = self._kpi_history.get("precision", [])
        return {
            "mttd_seconds": {
                "mean": round(statistics.mean(mttd), 2) if mttd else 0,
                "p50": round(sorted(mttd)[len(mttd)//2], 2) if mttd else 0,
                "p95": round(sorted(mttd)[int(len(mttd)*0.95)], 2) if len(mttd) > 1 else 0,
            },
            "mttr_seconds": {
                "mean": round(statistics.mean(mttr), 2) if mttr else 0,
                "p50": round(sorted(mttr)[len(mttr)//2], 2) if mttr else 0,
                "p95": round(sorted(mttr)[int(len(mttr)*0.95)], 2) if len(mttr) > 1 else 0,
            },
            "alert_precision": round(statistics.mean(precision), 4) if precision else 1.0,
            "false_positive_rate": round(1.0 - (statistics.mean(precision) if precision else 1.0), 4),
            "total_detections": len(self._detections),
            "total_incidents": len(self._incidents),
        }

    def get_stats(self) -> Dict:
        return self.get_kpis()


# ============================================================================
#  LOG CORRELATION ENGINE
# ============================================================================

class CorrelationRule:
    def __init__(self, rule_id, name, pattern, window_sec, min_events, severity):
        self.rule_id = rule_id
        self.name = name
        self.pattern = pattern  # Dict of field→value patterns
        self.window_sec = window_sec
        self.min_events = min_events
        self.severity = severity

    def to_dict(self):
        return {"id": self.rule_id, "name": self.name,
                "window_sec": self.window_sec, "min_events": self.min_events,
                "severity": self.severity}


class LogCorrelationEngine:
    """SIEM-style cross-source log correlation."""

    def __init__(self):
        self._rules: List[CorrelationRule] = []
        self._correlations: List[Dict] = []
        self._seed()

    def _seed(self):
        rules = [
            ("COR-001", "Brute Force Attack",
             {"type": "auth", "severity": "high"}, 300, 10, "critical"),
            ("COR-002", "Lateral Movement",
             {"type": "access"}, 600, 5, "critical"),
            ("COR-003", "Data Exfiltration Burst",
             {"type": "dlp"}, 60, 3, "critical"),
            ("COR-004", "Privilege Escalation Chain",
             {"type": "auth", "severity": "critical"}, 300, 3, "critical"),
            ("COR-005", "Reconnaissance + Exploitation",
             {"type": "network"}, 900, 8, "high"),
            ("COR-006", "Multi-Source Auth Anomaly",
             {"type": "auth"}, 120, 5, "high"),
            ("COR-007", "Compliance Drift Storm",
             {"type": "compliance"}, 3600, 10, "medium"),
            ("COR-008", "System Health Cascade",
             {"type": "system"}, 300, 5, "high"),
        ]
        for rid, name, pattern, window, min_ev, sev in rules:
            self._rules.append(CorrelationRule(rid, name, pattern, window, min_ev, sev))

    def correlate(self, events: List[Dict]) -> List[Dict]:
        """Run correlation rules against a batch of events."""
        findings = []
        now = time.time()
        for rule in self._rules:
            matching = []
            for evt in events:
                matches = all(evt.get(k) == v for k, v in rule.pattern.items())
                if matches:
                    matching.append(evt)
            if len(matching) >= rule.min_events:
                finding = {
                    "rule": rule.to_dict(),
                    "matched_events": len(matching),
                    "confidence": min(1.0, len(matching) / (rule.min_events * 2)),
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
                findings.append(finding)
                self._correlations.append(finding)
        return findings

    def get_stats(self) -> Dict:
        return {"rules": len(self._rules),
                "correlations_found": len(self._correlations)}


# Singletons
data_lake = SecurityDataLake()
threat_analytics = ThreatAnalytics()
kpi_engine = SecurityKPIEngine()
log_correlator = LogCorrelationEngine()
