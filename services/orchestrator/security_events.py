"""
Security Event Correlation — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

SIEM-grade event pipeline that correlates security events
across subsystems to detect complex attack patterns.
Implements CEF (Common Event Format) compatible events.
"""

import collections
import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("qwen.sec_events")


class EventSeverity(int, Enum):
    """CEF severity levels (0-10)."""
    INFORMATIONAL = 1
    LOW = 3
    MEDIUM = 5
    HIGH = 7
    VERY_HIGH = 8
    CRITICAL = 10


class EventOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class SecurityEvent:
    """CEF-compatible security event."""
    __slots__ = [
        "event_id", "timestamp", "device_vendor", "device_product",
        "device_version", "signature_id", "name", "severity",
        "src_ip", "dst_ip", "src_user", "dst_user", "action",
        "outcome", "tenant_id", "request_id", "extensions",
    ]

    def __init__(self, signature_id: str, name: str, severity: EventSeverity,
                 src_ip="", src_user="", action="", outcome=EventOutcome.UNKNOWN,
                 tenant_id="", request_id="", **extensions):
        self.event_id = hashlib.sha256(
            f"{time.time()}-{signature_id}-{src_ip}".encode()
        ).hexdigest()[:16]
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.device_vendor = "LibertyCenter"
        self.device_product = "AsonVerification"
        self.device_version = "2.0"
        self.signature_id = signature_id
        self.name = name
        self.severity = severity
        self.src_ip = src_ip
        self.dst_ip = ""
        self.src_user = src_user
        self.dst_user = ""
        self.action = action
        self.outcome = outcome
        self.tenant_id = tenant_id
        self.request_id = request_id
        self.extensions = extensions

    def to_cef(self) -> str:
        """Format as CEF string for SIEM ingestion."""
        ext_parts = [f"src={self.src_ip}", f"suser={self.src_user}",
                     f"act={self.action}", f"outcome={self.outcome.value}",
                     f"tenantId={self.tenant_id}", f"requestId={self.request_id}"]
        for k, v in self.extensions.items():
            ext_parts.append(f"{k}={v}")
        ext_str = " ".join(ext_parts)
        return (f"CEF:0|{self.device_vendor}|{self.device_product}|"
                f"{self.device_version}|{self.signature_id}|{self.name}|"
                f"{self.severity.value}|{ext_str}")

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id, "timestamp": self.timestamp,
            "signature_id": self.signature_id, "name": self.name,
            "severity": self.severity.value, "src_ip": self.src_ip,
            "src_user": self.src_user, "action": self.action,
            "outcome": self.outcome.value, "tenant_id": self.tenant_id,
            "extensions": self.extensions,
        }


# ============================================================================
#  CORRELATION RULES
# ============================================================================

class CorrelationRule:
    """A rule that detects patterns across multiple events."""

    def __init__(self, rule_id: str, name: str, description: str,
                 window_seconds: int, threshold: int,
                 match_fn: Callable[[SecurityEvent], bool],
                 alert_severity: EventSeverity = EventSeverity.HIGH):
        self.rule_id = rule_id
        self.name = name
        self.description = description
        self.window_seconds = window_seconds
        self.threshold = threshold
        self.match_fn = match_fn
        self.alert_severity = alert_severity
        self._matches: collections.deque = collections.deque(maxlen=10000)
        self.triggered_count = 0

    def evaluate(self, event: SecurityEvent) -> Optional[Dict]:
        if not self.match_fn(event):
            return None
        now = time.time()
        self._matches.append(now)
        # Count matches in window
        cutoff = now - self.window_seconds
        in_window = sum(1 for t in self._matches if t > cutoff)
        if in_window >= self.threshold:
            self.triggered_count += 1
            self._matches.clear()  # Reset after trigger
            return {
                "rule_id": self.rule_id, "rule_name": self.name,
                "severity": self.alert_severity.value,
                "matches_in_window": in_window,
                "window_seconds": self.window_seconds,
                "triggered_at": datetime.now(timezone.utc).isoformat(),
            }
        return None


# ============================================================================
#  CORRELATION ENGINE
# ============================================================================

class SecurityEventCorrelator:
    """
    Correlates security events to detect complex attack patterns.
    All processing is local — no external SIEM service.
    """

    def __init__(self, max_events: int = 50000):
        self._events: collections.deque = collections.deque(maxlen=max_events)
        self._rules: Dict[str, CorrelationRule] = {}
        self._correlated_alerts: List[Dict] = []
        self._lock = threading.Lock()
        self._register_default_rules()

    def _register_default_rules(self):
        # R1: Distributed brute force (many sources, same target)
        self.add_rule(CorrelationRule(
            "CORR-001", "Distributed Brute Force",
            "Multiple auth failures from different sources targeting same account",
            window_seconds=300, threshold=10,
            match_fn=lambda e: e.signature_id == "AUTH_FAILURE",
            alert_severity=EventSeverity.CRITICAL,
        ))
        # R2: Privilege escalation attempt
        self.add_rule(CorrelationRule(
            "CORR-002", "Privilege Escalation Attempt",
            "Multiple 403 responses followed by admin endpoint access",
            window_seconds=120, threshold=5,
            match_fn=lambda e: e.outcome == EventOutcome.FAILURE and "admin" in e.action,
            alert_severity=EventSeverity.CRITICAL,
        ))
        # R3: Data exfiltration (bulk export)
        self.add_rule(CorrelationRule(
            "CORR-003", "Bulk Data Export",
            "Excessive audit/data export within short window",
            window_seconds=600, threshold=20,
            match_fn=lambda e: "export" in e.action.lower(),
            alert_severity=EventSeverity.HIGH,
        ))
        # R4: Account compromise (auth success from new geo after failures)
        self.add_rule(CorrelationRule(
            "CORR-004", "Suspicious Auth After Failures",
            "Successful auth immediately following multiple failures",
            window_seconds=60, threshold=3,
            match_fn=lambda e: e.signature_id == "AUTH_FAILURE",
            alert_severity=EventSeverity.HIGH,
        ))
        # R5: API scanning / enumeration
        self.add_rule(CorrelationRule(
            "CORR-005", "API Enumeration Detected",
            "Rapid sequential requests to many distinct endpoints",
            window_seconds=60, threshold=30,
            match_fn=lambda e: e.outcome == EventOutcome.FAILURE and e.severity.value <= 3,
            alert_severity=EventSeverity.MEDIUM,
        ))
        # R6: Coordinated attack (multiple tenants, same pattern)
        self.add_rule(CorrelationRule(
            "CORR-006", "Cross-Tenant Attack Pattern",
            "Same attack signature observed across multiple tenants",
            window_seconds=300, threshold=5,
            match_fn=lambda e: e.severity.value >= EventSeverity.HIGH.value,
            alert_severity=EventSeverity.CRITICAL,
        ))

    def add_rule(self, rule: CorrelationRule):
        self._rules[rule.rule_id] = rule

    def ingest(self, event: SecurityEvent) -> List[Dict]:
        """Ingest an event and check all correlation rules."""
        with self._lock:
            self._events.append(event)

        triggered = []
        for rule in self._rules.values():
            result = rule.evaluate(event)
            if result:
                result["triggering_event"] = event.to_dict()
                triggered.append(result)
                with self._lock:
                    self._correlated_alerts.append(result)
                logger.warning(f"CORRELATION [{result['rule_name']}]: severity={result['severity']}")

        return triggered

    # Convenience emitters
    def emit_auth_failure(self, user: str, source_ip: str, tenant_id: str = "", reason: str = ""):
        return self.ingest(SecurityEvent(
            "AUTH_FAILURE", "Authentication Failure", EventSeverity.MEDIUM,
            src_ip=source_ip, src_user=user, action="login",
            outcome=EventOutcome.FAILURE, tenant_id=tenant_id, reason=reason,
        ))

    def emit_auth_success(self, user: str, source_ip: str, tenant_id: str = ""):
        return self.ingest(SecurityEvent(
            "AUTH_SUCCESS", "Authentication Success", EventSeverity.INFORMATIONAL,
            src_ip=source_ip, src_user=user, action="login",
            outcome=EventOutcome.SUCCESS, tenant_id=tenant_id,
        ))

    def emit_access_denied(self, user: str, resource: str, source_ip: str, tenant_id: str = ""):
        return self.ingest(SecurityEvent(
            "ACCESS_DENIED", "Authorization Denied", EventSeverity.HIGH,
            src_ip=source_ip, src_user=user, action=f"access:{resource}",
            outcome=EventOutcome.FAILURE, tenant_id=tenant_id,
        ))

    def emit_data_export(self, user: str, export_type: str, record_count: int, tenant_id: str = ""):
        return self.ingest(SecurityEvent(
            "DATA_EXPORT", "Data Export", EventSeverity.MEDIUM,
            src_user=user, action=f"export:{export_type}",
            outcome=EventOutcome.SUCCESS, tenant_id=tenant_id,
            record_count=record_count,
        ))

    def get_correlated_alerts(self, limit: int = 50) -> List[Dict]:
        return self._correlated_alerts[-limit:]

    def get_stats(self) -> Dict:
        return {
            "total_events": len(self._events),
            "correlation_rules": len(self._rules),
            "correlated_alerts": len(self._correlated_alerts),
            "rules": {r.rule_id: {"name": r.name, "triggered": r.triggered_count}
                      for r in self._rules.values()},
        }

event_correlator = SecurityEventCorrelator()
