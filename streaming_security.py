"""
Real-Time Streaming Security — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Event stream processing, hot-reloadable detection rules,
rolling-baseline anomaly detection.
"""

import hashlib, logging, math, statistics, threading, time
from collections import defaultdict, deque
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("qwen.streaming")


# ============================================================================
#  STREAM PROCESSOR
# ============================================================================

class WindowType(str, Enum):
    TUMBLING = "tumbling"   # Fixed non-overlapping windows
    SLIDING = "sliding"     # Overlapping windows
    SESSION = "session"     # Activity-based windows


class TimeWindow:
    def __init__(self, window_type: WindowType, duration_sec: int):
        self.window_type = window_type
        self.duration = duration_sec
        self.events: deque = deque()
        self._lock = threading.Lock()

    def add(self, event: Dict):
        with self._lock:
            event["_ingest_ts"] = time.time()
            self.events.append(event)
            self._evict()

    def _evict(self):
        cutoff = time.time() - self.duration
        while self.events and self.events[0].get("_ingest_ts", 0) < cutoff:
            self.events.popleft()

    def get_events(self) -> List[Dict]:
        with self._lock:
            self._evict()
            return list(self.events)

    @property
    def count(self):
        with self._lock:
            self._evict()
            return len(self.events)


class AggregationType(str, Enum):
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    DISTINCT = "distinct"


class StreamProcessor:
    """Event stream processor with windowed aggregation & CEP."""

    def __init__(self):
        self._windows: Dict[str, TimeWindow] = {}
        self._processed = 0
        self._cep_patterns: List[Dict] = []
        self._lock = threading.Lock()
        self._seed()

    def _seed(self):
        # Pre-configured windows
        self._windows["1min"] = TimeWindow(WindowType.TUMBLING, 60)
        self._windows["5min"] = TimeWindow(WindowType.TUMBLING, 300)
        self._windows["15min"] = TimeWindow(WindowType.TUMBLING, 900)
        self._windows["1hour"] = TimeWindow(WindowType.TUMBLING, 3600)

        # CEP patterns
        self._cep_patterns = [
            {"name": "rapid_auth_failures", "sequence": ["auth_fail", "auth_fail", "auth_fail"],
             "window_sec": 60, "severity": "critical"},
            {"name": "scan_then_exploit", "sequence": ["port_scan", "exploit_attempt"],
             "window_sec": 300, "severity": "critical"},
            {"name": "recon_then_exfil", "sequence": ["directory_enum", "data_download"],
             "window_sec": 600, "severity": "critical"},
            {"name": "priv_esc_chain", "sequence": ["normal_access", "admin_access", "config_change"],
             "window_sec": 300, "severity": "critical"},
            {"name": "credential_spray", "sequence": ["auth_fail"] * 5,
             "window_sec": 120, "severity": "high"},
        ]

    def ingest(self, event: Dict) -> Dict:
        """Ingest an event into all active windows."""
        self._processed += 1
        for window in self._windows.values():
            window.add(event)
        return {"ingested": True, "total": self._processed}

    def aggregate(self, window_name: str, field: str,
                  agg_type: AggregationType = AggregationType.COUNT) -> Dict:
        window = self._windows.get(window_name)
        if not window:
            return {"error": f"Window {window_name} not found"}
        events = window.get_events()
        if agg_type == AggregationType.COUNT:
            result = len(events)
        elif agg_type == AggregationType.DISTINCT:
            result = len(set(e.get(field, "") for e in events))
        else:
            values = [e.get(field, 0) for e in events if isinstance(e.get(field), (int, float))]
            if not values:
                result = 0
            elif agg_type == AggregationType.SUM:
                result = sum(values)
            elif agg_type == AggregationType.AVG:
                result = statistics.mean(values)
            elif agg_type == AggregationType.MIN:
                result = min(values)
            elif agg_type == AggregationType.MAX:
                result = max(values)
            else:
                result = len(events)
        return {"window": window_name, "field": field,
                "aggregation": agg_type.value, "result": result,
                "event_count": window.count}

    def check_cep(self, window_name: str = "5min") -> List[Dict]:
        """Check Complex Event Processing patterns."""
        window = self._windows.get(window_name)
        if not window:
            return []
        events = window.get_events()
        event_types = [e.get("type", "") for e in events]
        triggered = []
        for pattern in self._cep_patterns:
            seq = pattern["sequence"]
            # Check if sequence exists in event stream
            idx = 0
            for et in event_types:
                if idx < len(seq) and et == seq[idx]:
                    idx += 1
            if idx >= len(seq):
                triggered.append({
                    "pattern": pattern["name"],
                    "severity": pattern["severity"],
                    "matched": True,
                    "ts": datetime.now(timezone.utc).isoformat()})
        return triggered

    def get_stats(self) -> Dict:
        return {
            "processed": self._processed,
            "windows": {k: v.count for k, v in self._windows.items()},
            "cep_patterns": len(self._cep_patterns),
        }


# ============================================================================
#  REAL-TIME RULES ENGINE
# ============================================================================

class RuleAction(str, Enum):
    ALERT = "alert"
    BLOCK = "block"
    LOG = "log"
    ESCALATE = "escalate"
    ENRICH = "enrich"


class DetectionRule:
    def __init__(self, rule_id, name, condition, action, severity, enabled=True):
        self.rule_id = rule_id
        self.name = name
        self.condition = condition  # Dict of field→value or callable
        self.action = action
        self.severity = severity
        self.enabled = enabled
        self.matches = 0
        self.last_match: Optional[str] = None

    def to_dict(self):
        return {"id": self.rule_id, "name": self.name,
                "action": self.action.value, "severity": self.severity,
                "enabled": self.enabled, "matches": self.matches}


class RealTimeRulesEngine:
    """Hot-reloadable detection rules executed on live streams."""

    def __init__(self):
        self._rules: Dict[str, DetectionRule] = {}
        self._counter = 0
        self._match_log: List[Dict] = []
        self._seed()

    def _seed(self):
        rules = [
            ("SQL injection attempt", {"pattern": r"(?:UNION|SELECT|DROP|INSERT).*(?:FROM|INTO|TABLE)"},
             RuleAction.BLOCK, "critical"),
            ("XSS payload", {"pattern": r"<script[^>]*>"},
             RuleAction.BLOCK, "critical"),
            ("Path traversal", {"pattern": r"\.\./\.\./"},
             RuleAction.BLOCK, "high"),
            ("Suspicious user-agent", {"pattern": r"(?:sqlmap|nikto|nmap|burp|dirbuster)"},
             RuleAction.ALERT, "high"),
            ("Rate limit exceeded", {"field": "rate", "threshold": 100},
             RuleAction.BLOCK, "medium"),
            ("Failed auth spike", {"field": "auth_failures", "threshold": 5},
             RuleAction.ESCALATE, "high"),
            ("Large data transfer", {"field": "bytes_out", "threshold": 104857600},
             RuleAction.ALERT, "medium"),
            ("Admin API access", {"field": "path", "value": "/admin"},
             RuleAction.LOG, "low"),
            ("Crypto key access", {"field": "resource", "value": "key_store"},
             RuleAction.LOG, "medium"),
            ("Service account lateral", {"field": "actor_type", "value": "service_account"},
             RuleAction.ALERT, "medium"),
        ]
        for name, condition, action, severity in rules:
            self._counter += 1
            rid = f"RTR-{self._counter:06d}"
            self._rules[rid] = DetectionRule(rid, name, condition, action, severity)

    def add_rule(self, name, condition, action, severity) -> str:
        self._counter += 1
        rid = f"RTR-{self._counter:06d}"
        self._rules[rid] = DetectionRule(rid, name, condition, action, severity)
        return rid

    def remove_rule(self, rule_id: str) -> bool:
        return self._rules.pop(rule_id, None) is not None

    def toggle_rule(self, rule_id: str, enabled: bool) -> Dict:
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = enabled
            return {"toggled": True, "enabled": enabled}
        return {"error": "Rule not found"}

    def evaluate(self, event: Dict) -> List[Dict]:
        """Evaluate all rules against an event."""
        matches = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            matched = False
            cond = rule.condition
            if "pattern" in cond:
                import re
                text = str(event.get("content", "")) + str(event.get("path", ""))
                if re.search(cond["pattern"], text, re.IGNORECASE):
                    matched = True
            elif "field" in cond and "threshold" in cond:
                val = event.get(cond["field"], 0)
                if isinstance(val, (int, float)) and val > cond["threshold"]:
                    matched = True
            elif "field" in cond and "value" in cond:
                if event.get(cond["field"]) == cond["value"]:
                    matched = True
            if matched:
                rule.matches += 1
                rule.last_match = datetime.now(timezone.utc).isoformat()
                match_record = {"rule": rule.to_dict(), "event_id": event.get("id", ""),
                               "action": rule.action.value}
                matches.append(match_record)
                self._match_log.append(match_record)
        return matches

    def get_stats(self) -> Dict:
        return {"rules": len(self._rules),
                "enabled": sum(1 for r in self._rules.values() if r.enabled),
                "total_matches": sum(r.matches for r in self._rules.values())}


# ============================================================================
#  ANOMALY DETECTOR
# ============================================================================

class AnomalyDetector:
    """Rolling baseline with Z-score anomaly detection."""

    def __init__(self, window_size: int = 100, z_threshold: float = 3.0):
        self._baselines: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._z_threshold = z_threshold
        self._anomalies: List[Dict] = []
        self._checks = 0

    def observe(self, metric: str, value: float) -> Dict:
        self._checks += 1
        baseline = self._baselines[metric]
        result = {"metric": metric, "value": value, "anomaly": False}

        if len(baseline) >= 10:
            bl = list(baseline)
            mean = statistics.mean(bl)
            stdev = statistics.stdev(bl) or 0.001
            z = (value - mean) / stdev
            result.update({
                "mean": round(mean, 4), "stdev": round(stdev, 4),
                "z_score": round(z, 4),
                "anomaly": abs(z) > self._z_threshold,
                "direction": "spike" if z > 0 else "drop",
            })
            if result["anomaly"]:
                result["ts"] = datetime.now(timezone.utc).isoformat()
                self._anomalies.append(result)

        baseline.append(value)
        return result

    def get_anomalies(self, limit: int = 20) -> List[Dict]:
        return self._anomalies[-limit:]

    def get_stats(self) -> Dict:
        return {"metrics_monitored": len(self._baselines),
                "checks": self._checks,
                "anomalies": len(self._anomalies),
                "z_threshold": self._z_threshold}


# Singletons
stream_processor = StreamProcessor()
realtime_rules = RealTimeRulesEngine()
anomaly_detector = AnomalyDetector()
