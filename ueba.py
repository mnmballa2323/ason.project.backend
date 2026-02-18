"""
Behavioral Biometrics & UEBA — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

User & Entity Behavior Analytics, behavioral biometrics,
insider threat detection.
"""

import hashlib, logging, math, statistics, threading, time
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.ueba")


# ============================================================================
#  UEBA ENGINE
# ============================================================================

class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class EntityProfile:
    def __init__(self, entity_id: str, entity_type: str = "user"):
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.risk_score = 0.0
        self.baseline_hours: List[int] = []
        self.baseline_ips: List[str] = []
        self.baseline_endpoints: List[str] = []
        self.baseline_data_volume: List[float] = []
        self.session_count = 0
        self.anomaly_count = 0
        self.last_seen: Optional[str] = None
        self.flags: List[str] = []

    def update_risk(self, delta: float):
        self.risk_score = max(0, min(100, self.risk_score + delta))

    @property
    def risk_level(self) -> RiskLevel:
        if self.risk_score >= 80: return RiskLevel.CRITICAL
        if self.risk_score >= 60: return RiskLevel.HIGH
        if self.risk_score >= 40: return RiskLevel.MEDIUM
        if self.risk_score >= 20: return RiskLevel.LOW
        return RiskLevel.MINIMAL

    def to_dict(self):
        return {"id": self.entity_id, "type": self.entity_type,
                "risk_score": round(self.risk_score, 2),
                "risk_level": self.risk_level.value,
                "sessions": self.session_count,
                "anomalies": self.anomaly_count,
                "flags": self.flags}


class UEBAEngine:
    """User & Entity Behavior Analytics — session profiling, risk scoring."""

    RISK_FACTORS = {
        "new_ip": 15,
        "unusual_hour": 10,
        "new_endpoint": 5,
        "high_data_volume": 20,
        "rapid_actions": 10,
        "failed_auth": 15,
        "privilege_escalation": 25,
        "impossible_travel": 30,
        "dormant_reactivation": 20,
    }

    def __init__(self):
        self._profiles: Dict[str, EntityProfile] = {}
        self._sessions: List[Dict] = []
        self._lock = threading.Lock()

    def get_or_create_profile(self, entity_id: str) -> EntityProfile:
        if entity_id not in self._profiles:
            self._profiles[entity_id] = EntityProfile(entity_id)
        return self._profiles[entity_id]

    def analyze_session(self, entity_id: str, ip: str, hour: int,
                       endpoint: str, data_bytes: float = 0,
                       action_count: int = 1) -> Dict:
        profile = self.get_or_create_profile(entity_id)
        profile.session_count += 1
        profile.last_seen = datetime.now(timezone.utc).isoformat()
        anomalies = []

        # New IP detection
        if ip not in profile.baseline_ips:
            anomalies.append("new_ip")
            profile.update_risk(self.RISK_FACTORS["new_ip"])
            if len(profile.baseline_ips) < 20:
                profile.baseline_ips.append(ip)

        # Unusual hour
        if profile.baseline_hours and hour not in profile.baseline_hours:
            anomalies.append("unusual_hour")
            profile.update_risk(self.RISK_FACTORS["unusual_hour"])
        if len(profile.baseline_hours) < 24:
            profile.baseline_hours.append(hour)

        # High data volume
        if profile.baseline_data_volume:
            avg = statistics.mean(profile.baseline_data_volume) if profile.baseline_data_volume else 0
            if data_bytes > avg * 3 and avg > 0:
                anomalies.append("high_data_volume")
                profile.update_risk(self.RISK_FACTORS["high_data_volume"])
        profile.baseline_data_volume.append(data_bytes)
        if len(profile.baseline_data_volume) > 100:
            profile.baseline_data_volume = profile.baseline_data_volume[-100:]

        # Rapid actions
        if action_count > 50:
            anomalies.append("rapid_actions")
            profile.update_risk(self.RISK_FACTORS["rapid_actions"])

        profile.anomaly_count += len(anomalies)
        # Decay risk over time (baseline learning)
        if not anomalies:
            profile.update_risk(-2)

        session = {"entity": entity_id, "anomalies": anomalies,
                  "risk_score": profile.risk_score,
                  "risk_level": profile.risk_level.value,
                  "ts": profile.last_seen}
        self._sessions.append(session)
        return session

    def flag_impossible_travel(self, entity_id: str, location_a: str,
                              location_b: str, minutes_between: int) -> Dict:
        profile = self.get_or_create_profile(entity_id)
        if minutes_between < 120:  # Less than 2 hours
            profile.update_risk(self.RISK_FACTORS["impossible_travel"])
            profile.flags.append(f"impossible_travel:{location_a}→{location_b}")
            profile.anomaly_count += 1
            return {"flagged": True, "risk": profile.risk_score}
        return {"flagged": False}

    def get_high_risk(self, threshold: float = 60) -> List[Dict]:
        return [p.to_dict() for p in self._profiles.values() if p.risk_score >= threshold]

    def get_stats(self) -> Dict:
        return {"entities": len(self._profiles),
                "sessions": len(self._sessions),
                "high_risk": len(self.get_high_risk())}


# ============================================================================
#  BEHAVIORAL BIOMETRICS
# ============================================================================

class BiometricProfile:
    def __init__(self, user_id):
        self.user_id = user_id
        self.typing_intervals: List[float] = []
        self.typing_hold_times: List[float] = []
        self.navigation_sequence: List[str] = []
        self.click_patterns: List[Dict] = []
        self.session_durations: List[float] = []
        self.mouse_velocities: List[float] = []
        self.trained = False
        self.confidence_threshold = 0.7

    def to_dict(self):
        return {"user_id": self.user_id, "trained": self.trained,
                "samples_typing": len(self.typing_intervals),
                "samples_navigation": len(self.navigation_sequence)}


class BehavioralBiometrics:
    """Typing cadence, navigation patterns, session fingerprinting."""

    def __init__(self):
        self._profiles: Dict[str, BiometricProfile] = {}
        self._authentications = 0

    def train(self, user_id: str, typing_intervals: List[float],
              navigation: List[str], session_duration: float) -> Dict:
        if user_id not in self._profiles:
            self._profiles[user_id] = BiometricProfile(user_id)
        profile = self._profiles[user_id]
        profile.typing_intervals.extend(typing_intervals)
        profile.navigation_sequence.extend(navigation)
        profile.session_durations.append(session_duration)
        if len(profile.typing_intervals) >= 50:
            profile.trained = True
        return {"trained": profile.trained,
                "samples": len(profile.typing_intervals)}

    def authenticate(self, user_id: str, typing_intervals: List[float],
                    navigation: List[str]) -> Dict:
        self._authentications += 1
        profile = self._profiles.get(user_id)
        if not profile or not profile.trained:
            return {"match": True, "confidence": 0.5, "reason": "no_baseline"}

        # Typing cadence comparison (simplified Euclidean distance)
        baseline_mean = statistics.mean(profile.typing_intervals) if profile.typing_intervals else 0
        baseline_std = statistics.stdev(profile.typing_intervals) if len(profile.typing_intervals) > 1 else 1
        current_mean = statistics.mean(typing_intervals) if typing_intervals else 0
        typing_distance = abs(current_mean - baseline_mean) / max(baseline_std, 0.001)
        typing_score = max(0, 1.0 - typing_distance * 0.2)

        # Navigation pattern match
        baseline_nav = set(profile.navigation_sequence[-20:]) if profile.navigation_sequence else set()
        current_nav = set(navigation)
        if baseline_nav:
            nav_overlap = len(baseline_nav & current_nav) / max(len(baseline_nav), 1)
        else:
            nav_overlap = 0.5

        confidence = (typing_score * 0.6 + nav_overlap * 0.4)
        return {
            "match": confidence >= profile.confidence_threshold,
            "confidence": round(confidence, 4),
            "typing_score": round(typing_score, 4),
            "navigation_score": round(nav_overlap, 4),
        }

    def get_stats(self) -> Dict:
        return {"profiles": len(self._profiles),
                "authentications": self._authentications,
                "trained": sum(1 for p in self._profiles.values() if p.trained)}


# ============================================================================
#  INSIDER THREAT DETECTOR
# ============================================================================

class InsiderIndicator(str, Enum):
    DATA_HOARDING = "data_hoarding"
    OFF_HOURS_ACCESS = "off_hours_access"
    MASS_DOWNLOAD = "mass_download"
    PRIV_ESCALATION = "privilege_escalation"
    RESIGNATION_RISK = "resignation_risk"
    UNAUTHORIZED_TOOL = "unauthorized_tool"
    USB_EXFIL = "usb_exfiltration"
    EMAIL_FORWARD = "email_forwarding"
    POLICY_BYPASS = "policy_bypass"


class InsiderThreatDetector:
    """Detect insider threats — data hoarding, off-hours, privilege abuse."""

    RULES = [
        {"indicator": InsiderIndicator.DATA_HOARDING,
         "condition": "data_access_count > 100 in 24h",
         "threshold": 100, "severity": "high"},
        {"indicator": InsiderIndicator.OFF_HOURS_ACCESS,
         "condition": "access_hour not in [8-18]",
         "threshold": None, "severity": "medium"},
        {"indicator": InsiderIndicator.MASS_DOWNLOAD,
         "condition": "download_bytes > 500MB in 1h",
         "threshold": 524288000, "severity": "critical"},
        {"indicator": InsiderIndicator.PRIV_ESCALATION,
         "condition": "role_change without approval",
         "threshold": None, "severity": "critical"},
        {"indicator": InsiderIndicator.UNAUTHORIZED_TOOL,
         "condition": "tool not in approved_list",
         "threshold": None, "severity": "high"},
        {"indicator": InsiderIndicator.USB_EXFIL,
         "condition": "usb_write detected",
         "threshold": None, "severity": "critical"},
        {"indicator": InsiderIndicator.EMAIL_FORWARD,
         "condition": "auto-forward to external domain",
         "threshold": None, "severity": "high"},
        {"indicator": InsiderIndicator.POLICY_BYPASS,
         "condition": "security_policy override",
         "threshold": None, "severity": "critical"},
    ]

    def __init__(self):
        self._user_activity: Dict[str, List[Dict]] = defaultdict(list)
        self._alerts: List[Dict] = []
        self._risk_scores: Dict[str, float] = defaultdict(float)

    def record_activity(self, user_id: str, activity_type: str,
                       details: Dict = None) -> Dict:
        record = {"type": activity_type, "details": details or {},
                  "ts": time.time()}
        self._user_activity[user_id].append(record)
        if len(self._user_activity[user_id]) > 200:
            self._user_activity[user_id] = self._user_activity[user_id][-200:]
        alerts = self._evaluate(user_id)
        return {"alerts": alerts, "risk_score": self._risk_scores[user_id]}

    def _evaluate(self, user_id: str) -> List[Dict]:
        alerts = []
        activities = self._user_activity[user_id]
        recent = [a for a in activities if time.time() - a["ts"] < 86400]

        # Data hoarding
        data_access = [a for a in recent if a["type"] == "data_access"]
        if len(data_access) > 100:
            self._risk_scores[user_id] += 20
            alerts.append({"indicator": "data_hoarding", "count": len(data_access)})

        # Off-hours
        off_hours = [a for a in recent if a["type"] == "access" and
                     a.get("details", {}).get("hour", 12) not in range(8, 19)]
        if len(off_hours) > 5:
            self._risk_scores[user_id] += 10
            alerts.append({"indicator": "off_hours_access", "count": len(off_hours)})

        # Mass download
        downloads = sum(a.get("details", {}).get("bytes", 0)
                       for a in recent if a["type"] == "download")
        if downloads > 524288000:
            self._risk_scores[user_id] += 30
            alerts.append({"indicator": "mass_download", "bytes": downloads})

        self._risk_scores[user_id] = min(100, self._risk_scores[user_id])
        for alert in alerts:
            alert["user_id"] = user_id
            alert["ts"] = datetime.now(timezone.utc).isoformat()
            self._alerts.append(alert)
        return alerts

    def get_high_risk_users(self, threshold: float = 50) -> List[Dict]:
        return [{"user_id": uid, "risk_score": score}
                for uid, score in self._risk_scores.items() if score >= threshold]

    def get_stats(self) -> Dict:
        return {"tracked_users": len(self._user_activity),
                "alerts": len(self._alerts),
                "high_risk": len(self.get_high_risk_users())}


# Singletons
ueba_engine = UEBAEngine()
behavioral_biometrics = BehavioralBiometrics()
insider_threat = InsiderThreatDetector()
