"""
Security Alerting Engine — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Threshold, anomaly, and composite alerts. No external notifications.
"""

import logging, threading, time
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("qwen.alerting")


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertState(str, Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    SILENCED = "silenced"
    ACKNOWLEDGED = "acknowledged"


class AlertRule:
    def __init__(self, rule_id, name, condition_desc, severity,
                 threshold=None, check_fn=None):
        self.rule_id = rule_id
        self.name = name
        self.condition = condition_desc
        self.severity = severity
        self.threshold = threshold
        self.check_fn = check_fn
        self.enabled = True
        self.fire_count = 0
        self.last_fired: Optional[str] = None

    def to_dict(self):
        return {"id": self.rule_id, "name": self.name,
                "severity": self.severity.value,
                "enabled": self.enabled, "fires": self.fire_count}


class Alert:
    def __init__(self, alert_id, rule: AlertRule, message: str, data: Dict = None):
        self.alert_id = alert_id
        self.rule = rule
        self.message = message
        self.data = data or {}
        self.state = AlertState.FIRING
        self.fired_at = datetime.now(timezone.utc).isoformat()
        self.resolved_at: Optional[str] = None
        self.acknowledged_by: Optional[str] = None

    def to_dict(self):
        return {"id": self.alert_id, "rule": self.rule.name,
                "severity": self.rule.severity.value,
                "state": self.state.value,
                "message": self.message[:100],
                "fired_at": self.fired_at}


class SecurityAlertingEngine:
    """Threshold and anomaly-based security alerting."""

    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: List[Alert] = []
        self._counter = 0
        self._rule_counter = 0
        self._lock = threading.Lock()
        self._seed()

    def _seed(self):
        rules = [
            ("Auth failures exceed threshold", "auth_failures_total > 10 in 5min",
             AlertSeverity.HIGH, 10),
            ("Critical threat detected", "threat_level == critical",
             AlertSeverity.CRITICAL, None),
            ("DLP: restricted data exfiltration", "dlp_restricted_findings > 0",
             AlertSeverity.CRITICAL, 1),
            ("Containment escalation to lockdown", "containment_level >= 4",
             AlertSeverity.CRITICAL, 4),
            ("SOAR SLA breach", "incident_response_time > sla_minutes",
             AlertSeverity.HIGH, 15),
            ("Compliance drift detected", "compliance_score < 95%",
             AlertSeverity.HIGH, 95),
            ("Module health check failure", "module_health != healthy",
             AlertSeverity.MEDIUM, None),
            ("High-entropy data egress", "entropy_score > 7.9",
             AlertSeverity.HIGH, 7.9),
            ("Deception asset triggered", "deception_interaction > 0",
             AlertSeverity.CRITICAL, 1),
            ("Key rotation overdue", "key_age_days > rotation_policy",
             AlertSeverity.MEDIUM, 90),
        ]
        for name, condition, severity, threshold in rules:
            self._rule_counter += 1
            rid = f"ALR-{self._rule_counter:06d}"
            self._rules[rid] = AlertRule(rid, name, condition, severity, threshold)

    def fire(self, rule_id: str, message: str, data: Dict = None) -> Optional[Alert]:
        rule = self._rules.get(rule_id)
        if not rule or not rule.enabled:
            return None
        with self._lock:
            self._counter += 1
            alert_id = f"ALERT-{self._counter:010d}"
        rule.fire_count += 1
        rule.last_fired = datetime.now(timezone.utc).isoformat()
        alert = Alert(alert_id, rule, message, data)
        self._alerts.append(alert)
        logger.warning(f"ALERT {alert_id}: [{rule.severity.value}] {message[:80]}")
        return alert

    def acknowledge(self, alert_id: str, user: str) -> Dict:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.state = AlertState.ACKNOWLEDGED
                alert.acknowledged_by = user
                return {"acknowledged": True, "by": user}
        return {"error": "Alert not found"}

    def resolve(self, alert_id: str) -> Dict:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.state = AlertState.RESOLVED
                alert.resolved_at = datetime.now(timezone.utc).isoformat()
                return {"resolved": True}
        return {"error": "Alert not found"}

    def get_firing(self) -> List[Dict]:
        return [a.to_dict() for a in self._alerts if a.state == AlertState.FIRING]

    def get_stats(self) -> Dict:
        return {
            "rules": len(self._rules),
            "total_alerts": len(self._alerts),
            "firing": sum(1 for a in self._alerts if a.state == AlertState.FIRING),
            "resolved": sum(1 for a in self._alerts if a.state == AlertState.RESOLVED),
        }


security_alerting = SecurityAlertingEngine()
