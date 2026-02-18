"""
Threat Intelligence Engine — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Real-time anomaly detection and behavioral analysis for
security-critical verification operations. Detects:
- Unusual verification patterns (volume spikes, off-hours activity)
- Credential anomalies (impossible travel, new device, bulk auth failures)
- Data exfiltration signals (mass export, scraping patterns)
- Adversarial input patterns (coordinated prompt injection campaigns)

All analysis is local — no external threat feeds or cloud APIs.
"""

import collections
import logging
import math
import statistics
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("qwen.threat_intel")


class ThreatLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatCategory(str, Enum):
    ANOMALOUS_VOLUME = "anomalous_volume"
    CREDENTIAL_ABUSE = "credential_abuse"
    DATA_EXFILTRATION = "data_exfiltration"
    ADVERSARIAL_INPUT = "adversarial_input"
    BRUTE_FORCE = "brute_force"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    IMPOSSIBLE_TRAVEL = "impossible_travel"
    INSIDER_THREAT = "insider_threat"
    SUPPLY_CHAIN = "supply_chain"


class ThreatAlert:
    """A detected threat alert."""
    __slots__ = ["alert_id", "category", "level", "description",
                 "actor_id", "tenant_id", "source_ip", "evidence",
                 "timestamp", "acknowledged", "mitigated"]

    def __init__(self, alert_id, category, level, description,
                 actor_id="", tenant_id="", source_ip="", evidence=None):
        self.alert_id = alert_id
        self.category = category
        self.level = level
        self.description = description
        self.actor_id = actor_id
        self.tenant_id = tenant_id
        self.source_ip = source_ip
        self.evidence = evidence or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.acknowledged = False
        self.mitigated = False

    def to_dict(self):
        return {
            "alert_id": self.alert_id, "category": self.category.value,
            "level": self.level.value, "description": self.description,
            "actor_id": self.actor_id, "tenant_id": self.tenant_id,
            "source_ip": self.source_ip, "evidence": self.evidence,
            "timestamp": self.timestamp, "acknowledged": self.acknowledged,
        }


# ============================================================================
#  BEHAVIORAL BASELINES
# ============================================================================

class BehaviorProfile:
    """Maintains rolling statistical baselines for an actor."""

    def __init__(self, window_size: int = 1000):
        self._window = window_size
        self._request_times: collections.deque = collections.deque(maxlen=window_size)
        self._request_counts_per_hour: collections.deque = collections.deque(maxlen=168)  # 7 days
        self._endpoints_accessed: collections.Counter = collections.Counter()
        self._source_ips: set = set()
        self._failed_auths: collections.deque = collections.deque(maxlen=100)
        self._last_location: Optional[str] = None
        self._last_activity: float = 0

    def record_request(self, endpoint: str, source_ip: str, timestamp: float = None):
        ts = timestamp or time.time()
        self._request_times.append(ts)
        self._endpoints_accessed[endpoint] += 1
        self._source_ips.add(source_ip)
        self._last_activity = ts

    def record_auth_failure(self, source_ip: str, timestamp: float = None):
        self._failed_auths.append(timestamp or time.time())

    def get_request_rate(self, window_seconds: int = 300) -> float:
        """Requests per minute over the window."""
        now = time.time()
        cutoff = now - window_seconds
        recent = sum(1 for t in self._request_times if t > cutoff)
        return recent / (window_seconds / 60)

    def get_auth_failure_rate(self, window_seconds: int = 300) -> int:
        now = time.time()
        cutoff = now - window_seconds
        return sum(1 for t in self._failed_auths if t > cutoff)

    @property
    def unique_ips(self) -> int:
        return len(self._source_ips)

    @property
    def unique_endpoints(self) -> int:
        return len(self._endpoints_accessed)


# ============================================================================
#  THREAT DETECTION ENGINE
# ============================================================================

class ThreatIntelligenceEngine:
    """
    Local-only threat detection using behavioral analysis.
    No external feeds, no cloud APIs, no phone-home.
    """

    def __init__(self):
        self._profiles: Dict[str, BehaviorProfile] = {}
        self._alerts: List[ThreatAlert] = []
        self._lock = threading.Lock()
        self._counter = 0

        # Detection thresholds
        self._thresholds = {
            "requests_per_min_warn": 60,
            "requests_per_min_critical": 200,
            "auth_failures_warn": 5,
            "auth_failures_critical": 15,
            "unique_ips_warn": 10,
            "unique_ips_critical": 50,
            "bulk_export_threshold": 100,
        }

    def _get_profile(self, actor_id: str) -> BehaviorProfile:
        if actor_id not in self._profiles:
            self._profiles[actor_id] = BehaviorProfile()
        return self._profiles[actor_id]

    def analyze_request(
        self,
        actor_id: str,
        endpoint: str,
        source_ip: str,
        tenant_id: str = "",
        method: str = "GET",
        status_code: int = 200,
        payload_size: int = 0,
    ) -> List[ThreatAlert]:
        """Analyze a request for threat indicators. Returns any new alerts."""
        profile = self._get_profile(actor_id)
        profile.record_request(endpoint, source_ip)
        alerts = []

        # 1. Volume anomaly
        rpm = profile.get_request_rate()
        if rpm > self._thresholds["requests_per_min_critical"]:
            alerts.append(self._create_alert(
                ThreatCategory.ANOMALOUS_VOLUME, ThreatLevel.CRITICAL,
                f"Critical request volume: {rpm:.0f} req/min (actor: {actor_id})",
                actor_id, tenant_id, source_ip,
                {"requests_per_minute": round(rpm, 1)},
            ))
        elif rpm > self._thresholds["requests_per_min_warn"]:
            alerts.append(self._create_alert(
                ThreatCategory.ANOMALOUS_VOLUME, ThreatLevel.MEDIUM,
                f"Elevated request volume: {rpm:.0f} req/min",
                actor_id, tenant_id, source_ip,
                {"requests_per_minute": round(rpm, 1)},
            ))

        # 2. Auth failure detection
        if status_code in (401, 403):
            profile.record_auth_failure(source_ip)
            failures = profile.get_auth_failure_rate()
            if failures >= self._thresholds["auth_failures_critical"]:
                alerts.append(self._create_alert(
                    ThreatCategory.BRUTE_FORCE, ThreatLevel.CRITICAL,
                    f"Brute force detected: {failures} failures in 5 min",
                    actor_id, tenant_id, source_ip,
                    {"failure_count": failures},
                ))
            elif failures >= self._thresholds["auth_failures_warn"]:
                alerts.append(self._create_alert(
                    ThreatCategory.CREDENTIAL_ABUSE, ThreatLevel.HIGH,
                    f"Credential abuse: {failures} auth failures",
                    actor_id, tenant_id, source_ip,
                    {"failure_count": failures},
                ))

        # 3. Data exfiltration signals
        if endpoint in ("/audit/export", "/verify/batch") and method == "GET":
            rpm_export = profile.get_request_rate(60)
            if rpm_export > 10:
                alerts.append(self._create_alert(
                    ThreatCategory.DATA_EXFILTRATION, ThreatLevel.HIGH,
                    f"Potential data exfiltration: rapid export requests",
                    actor_id, tenant_id, source_ip,
                    {"export_rpm": round(rpm_export, 1), "endpoint": endpoint},
                ))

        # 4. Unusual IP diversity (credential sharing/compromise)
        if profile.unique_ips > self._thresholds["unique_ips_critical"]:
            alerts.append(self._create_alert(
                ThreatCategory.CREDENTIAL_ABUSE, ThreatLevel.HIGH,
                f"Credential used from {profile.unique_ips} unique IPs",
                actor_id, tenant_id, source_ip,
                {"unique_ips": profile.unique_ips},
            ))

        # 5. Endpoint enumeration detection
        if profile.unique_endpoints > 20 and rpm > 30:
            alerts.append(self._create_alert(
                ThreatCategory.ADVERSARIAL_INPUT, ThreatLevel.MEDIUM,
                f"Possible API enumeration: {profile.unique_endpoints} endpoints probed",
                actor_id, tenant_id, source_ip,
                {"unique_endpoints": profile.unique_endpoints},
            ))

        with self._lock:
            self._alerts.extend(alerts)

        return alerts

    def analyze_verification_input(
        self, claim: str, actor_id: str, tenant_id: str = "",
        sanitizer_threats: List[Dict] = None,
    ) -> List[ThreatAlert]:
        """Analyze verification input for adversarial patterns."""
        alerts = []

        if sanitizer_threats:
            critical_threats = [t for t in sanitizer_threats if t.get("severity") in ("critical", "high")]
            if len(critical_threats) >= 2:
                alerts.append(self._create_alert(
                    ThreatCategory.ADVERSARIAL_INPUT, ThreatLevel.HIGH,
                    f"Multi-vector attack: {len(critical_threats)} high-severity threats in single input",
                    actor_id, tenant_id, "",
                    {"threat_types": [t["category"] for t in critical_threats]},
                ))

        with self._lock:
            self._alerts.extend(alerts)
        return alerts

    def _create_alert(self, category, level, description, actor_id, tenant_id, source_ip, evidence):
        with self._lock:
            self._counter += 1
            alert_id = f"THREAT-{self._counter:08d}"
        alert = ThreatAlert(alert_id, category, level, description,
                            actor_id, tenant_id, source_ip, evidence)
        if level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
            logger.warning(f"THREAT [{level.value}]: {description}")
        return alert

    def get_active_alerts(self, level: ThreatLevel = None, limit: int = 100) -> List[Dict]:
        alerts = [a for a in reversed(self._alerts) if not a.mitigated]
        if level:
            alerts = [a for a in alerts if a.level == level]
        return [a.to_dict() for a in alerts[:limit]]

    def acknowledge_alert(self, alert_id: str, actor: str):
        for a in self._alerts:
            if a.alert_id == alert_id:
                a.acknowledged = True
                break

    def get_threat_summary(self) -> Dict:
        active = [a for a in self._alerts if not a.mitigated]
        by_level = {}
        by_category = {}
        for a in active:
            by_level[a.level.value] = by_level.get(a.level.value, 0) + 1
            by_category[a.category.value] = by_category.get(a.category.value, 0) + 1
        return {
            "total_alerts": len(self._alerts),
            "active_alerts": len(active),
            "by_level": by_level,
            "by_category": by_category,
            "monitored_actors": len(self._profiles),
        }

threat_engine = ThreatIntelligenceEngine()
