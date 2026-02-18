"""
Advanced Persistent Threat Detector — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

MITRE ATT&CK-aligned kill chain analysis for detecting
multi-stage, low-and-slow attacks from nation-state adversaries.

NASDAQ 100 Requirement: detect reconnaissance → weaponization →
delivery → exploitation → installation → C2 → exfiltration.
"""

import collections
import logging
import math
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger("qwen.apt_detector")


class KillChainPhase(str, Enum):
    """Lockheed Martin Cyber Kill Chain + MITRE ATT&CK mapping."""
    RECONNAISSANCE = "reconnaissance"         # T1595, T1592
    INITIAL_ACCESS = "initial_access"         # T1190, T1133
    EXECUTION = "execution"                   # T1059, T1203
    PERSISTENCE = "persistence"               # T1098, T1136
    PRIVILEGE_ESCALATION = "privilege_escalation"  # T1068, T1548
    DEFENSE_EVASION = "defense_evasion"       # T1070, T1562
    CREDENTIAL_ACCESS = "credential_access"    # T1110, T1003
    DISCOVERY = "discovery"                   # T1087, T1083
    LATERAL_MOVEMENT = "lateral_movement"     # T1021, T1550
    COLLECTION = "collection"                 # T1005, T1560
    COMMAND_AND_CONTROL = "command_control"    # T1071, T1573
    EXFILTRATION = "exfiltration"             # T1048, T1567
    IMPACT = "impact"                         # T1485, T1486


class ThreatConfidence(str, Enum):
    CONFIRMED = "confirmed"     # 0.9+
    HIGH = "high"               # 0.7-0.89
    MEDIUM = "medium"           # 0.5-0.69
    LOW = "low"                 # 0.3-0.49
    INFORMATIONAL = "info"      # <0.3


class APTIndicator:
    """A single indicator of APT activity."""
    def __init__(self, phase, technique_id, description,
                 confidence, actor_id="", source_ip="", evidence=None):
        self.phase = phase
        self.technique_id = technique_id
        self.description = description
        self.confidence = confidence
        self.actor_id = actor_id
        self.source_ip = source_ip
        self.evidence = evidence or {}
        self.timestamp = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "phase": self.phase.value, "technique": self.technique_id,
            "description": self.description, "confidence": self.confidence,
            "actor_id": self.actor_id, "source_ip": self.source_ip,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
        }


class ActorProfile:
    """Tracks kill chain progression for a suspected adversary."""
    def __init__(self, actor_key):
        self.actor_key = actor_key
        self.indicators: List[APTIndicator] = []
        self.phases_observed: Set[str] = set()
        self.first_seen = datetime.now(timezone.utc)
        self.last_seen = self.first_seen
        self.risk_score = 0.0

    def add(self, indicator: APTIndicator):
        self.indicators.append(indicator)
        self.phases_observed.add(indicator.phase.value)
        self.last_seen = datetime.now(timezone.utc)
        self._recalculate_risk()

    def _recalculate_risk(self):
        """Risk escalates with kill chain progression."""
        phase_weights = {
            KillChainPhase.RECONNAISSANCE.value: 0.05,
            KillChainPhase.INITIAL_ACCESS.value: 0.15,
            KillChainPhase.EXECUTION.value: 0.20,
            KillChainPhase.PERSISTENCE.value: 0.25,
            KillChainPhase.PRIVILEGE_ESCALATION.value: 0.35,
            KillChainPhase.DEFENSE_EVASION.value: 0.30,
            KillChainPhase.CREDENTIAL_ACCESS.value: 0.40,
            KillChainPhase.DISCOVERY.value: 0.20,
            KillChainPhase.LATERAL_MOVEMENT.value: 0.50,
            KillChainPhase.COLLECTION.value: 0.45,
            KillChainPhase.COMMAND_AND_CONTROL.value: 0.60,
            KillChainPhase.EXFILTRATION.value: 0.80,
            KillChainPhase.IMPACT.value: 1.0,
        }
        self.risk_score = sum(
            phase_weights.get(p, 0.1) for p in self.phases_observed
        )
        # Multi-phase progression multiplier
        if len(self.phases_observed) >= 3:
            self.risk_score *= 1.5
        if len(self.phases_observed) >= 5:
            self.risk_score *= 2.0
        self.risk_score = min(10.0, self.risk_score)

    @property
    def confidence_level(self) -> ThreatConfidence:
        if self.risk_score >= 5.0:
            return ThreatConfidence.CONFIRMED
        elif self.risk_score >= 3.0:
            return ThreatConfidence.HIGH
        elif self.risk_score >= 1.5:
            return ThreatConfidence.MEDIUM
        elif self.risk_score >= 0.5:
            return ThreatConfidence.LOW
        return ThreatConfidence.INFORMATIONAL

    def to_dict(self):
        return {
            "actor": self.actor_key,
            "risk_score": round(self.risk_score, 2),
            "confidence": self.confidence_level.value,
            "phases": sorted(self.phases_observed),
            "kill_chain_coverage": f"{len(self.phases_observed)}/13",
            "indicators": len(self.indicators),
            "dwell_time_seconds": (self.last_seen - self.first_seen).total_seconds(),
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }


# ============================================================================
#  APT DETECTION RULES
# ============================================================================

APT_RULES = [
    # Reconnaissance
    {"phase": KillChainPhase.RECONNAISSANCE, "technique": "T1595.002",
     "trigger": "port_scan", "description": "Active port scanning detected"},
    {"phase": KillChainPhase.RECONNAISSANCE, "technique": "T1592.004",
     "trigger": "version_enum", "description": "Software version enumeration"},
    {"phase": KillChainPhase.RECONNAISSANCE, "technique": "T1589.001",
     "trigger": "user_enum", "description": "User/employee enumeration attempt"},

    # Initial Access
    {"phase": KillChainPhase.INITIAL_ACCESS, "technique": "T1190",
     "trigger": "exploit_public_app", "description": "Exploit attempt on public application"},
    {"phase": KillChainPhase.INITIAL_ACCESS, "technique": "T1078",
     "trigger": "valid_account_anomaly", "description": "Valid account used from anomalous location"},

    # Execution
    {"phase": KillChainPhase.EXECUTION, "technique": "T1059.001",
     "trigger": "script_execution", "description": "Suspicious script execution pattern"},

    # Persistence
    {"phase": KillChainPhase.PERSISTENCE, "technique": "T1098",
     "trigger": "account_manipulation", "description": "Account privilege escalation or new admin"},
    {"phase": KillChainPhase.PERSISTENCE, "technique": "T1136.001",
     "trigger": "new_account_creation", "description": "New account created outside normal processes"},

    # Privilege Escalation
    {"phase": KillChainPhase.PRIVILEGE_ESCALATION, "technique": "T1068",
     "trigger": "priv_esc_exploit", "description": "Privilege escalation exploit attempt"},

    # Defense Evasion
    {"phase": KillChainPhase.DEFENSE_EVASION, "technique": "T1070.001",
     "trigger": "log_clearing", "description": "Audit log clearing or modification attempt"},
    {"phase": KillChainPhase.DEFENSE_EVASION, "technique": "T1562.001",
     "trigger": "disable_security", "description": "Security tool disablement attempt"},

    # Credential Access
    {"phase": KillChainPhase.CREDENTIAL_ACCESS, "technique": "T1110.001",
     "trigger": "brute_force", "description": "Password brute force detected"},
    {"phase": KillChainPhase.CREDENTIAL_ACCESS, "technique": "T1003",
     "trigger": "cred_dump", "description": "Credential dumping behavior"},

    # Lateral Movement
    {"phase": KillChainPhase.LATERAL_MOVEMENT, "technique": "T1021.001",
     "trigger": "lateral_ssh", "description": "SSH lateral movement between services"},
    {"phase": KillChainPhase.LATERAL_MOVEMENT, "technique": "T1550.001",
     "trigger": "token_reuse", "description": "Token reuse across service boundaries"},

    # Collection
    {"phase": KillChainPhase.COLLECTION, "technique": "T1005",
     "trigger": "bulk_data_access", "description": "Bulk data access pattern"},
    {"phase": KillChainPhase.COLLECTION, "technique": "T1560.001",
     "trigger": "data_staging", "description": "Data staging/compression detected"},

    # C2
    {"phase": KillChainPhase.COMMAND_AND_CONTROL, "technique": "T1071.001",
     "trigger": "c2_http", "description": "Suspicious HTTP beaconing pattern"},
    {"phase": KillChainPhase.COMMAND_AND_CONTROL, "technique": "T1573",
     "trigger": "encrypted_channel", "description": "Encrypted C2 channel detected"},

    # Exfiltration
    {"phase": KillChainPhase.EXFILTRATION, "technique": "T1048.003",
     "trigger": "exfil_http", "description": "Data exfiltration over HTTP"},
    {"phase": KillChainPhase.EXFILTRATION, "technique": "T1567.002",
     "trigger": "cloud_exfil", "description": "Data exfiltration to cloud storage"},

    # Impact
    {"phase": KillChainPhase.IMPACT, "technique": "T1485",
     "trigger": "data_destruction", "description": "Data destruction attempt"},
    {"phase": KillChainPhase.IMPACT, "technique": "T1486",
     "trigger": "ransomware", "description": "Ransomware encryption behavior"},
]


class APTDetector:
    """Kill chain analysis for APT detection."""

    def __init__(self):
        self._actors: Dict[str, ActorProfile] = {}
        self._lock = threading.Lock()
        self._alerts: List[Dict] = []

    def observe(self, trigger: str, actor_key: str,
                source_ip: str = "", evidence: Dict = None,
                confidence: float = 0.7) -> Optional[Dict]:
        """Submit an observation for APT kill chain analysis."""
        matched_rules = [r for r in APT_RULES if r["trigger"] == trigger]
        if not matched_rules:
            return None

        with self._lock:
            if actor_key not in self._actors:
                self._actors[actor_key] = ActorProfile(actor_key)
            profile = self._actors[actor_key]

        for rule in matched_rules:
            indicator = APTIndicator(
                rule["phase"], rule["technique"], rule["description"],
                confidence, actor_key, source_ip, evidence or {},
            )
            profile.add(indicator)

        # Generate alert if risk escalates
        alert = None
        if profile.risk_score >= 3.0:
            alert = {
                "type": "apt_alert",
                "actor": actor_key,
                "risk_score": round(profile.risk_score, 2),
                "confidence": profile.confidence_level.value,
                "phases_observed": sorted(profile.phases_observed),
                "latest_trigger": trigger,
                "recommendation": self._recommend(profile),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._alerts.append(alert)
            logger.critical(f"APT ALERT [{profile.confidence_level.value}]: "
                          f"actor={actor_key} risk={profile.risk_score:.1f} "
                          f"phases={len(profile.phases_observed)}/13")

        return alert

    def _recommend(self, profile: ActorProfile) -> str:
        if profile.risk_score >= 7.0:
            return "IMMEDIATE CONTAINMENT: isolate affected systems, rotate all credentials, engage IR team"
        elif profile.risk_score >= 5.0:
            return "ACTIVE THREAT: initiate incident response, block source IPs, preserve evidence"
        elif profile.risk_score >= 3.0:
            return "ELEVATED RISK: increase monitoring, review access logs, alert SOC team"
        return "MONITOR: continue observation and log analysis"

    def get_actor_profiles(self, min_risk: float = 0.0) -> List[Dict]:
        return [p.to_dict() for p in self._actors.values()
                if p.risk_score >= min_risk]

    def get_kill_chain_heatmap(self) -> Dict:
        """Show which kill chain phases are most active."""
        heatmap = {p.value: 0 for p in KillChainPhase}
        for actor in self._actors.values():
            for indicator in actor.indicators:
                heatmap[indicator.phase.value] += 1
        return heatmap

    def get_stats(self) -> Dict:
        return {
            "tracked_actors": len(self._actors),
            "total_indicators": sum(len(a.indicators) for a in self._actors.values()),
            "high_risk_actors": sum(1 for a in self._actors.values() if a.risk_score >= 5.0),
            "alerts_generated": len(self._alerts),
            "rules_loaded": len(APT_RULES),
            "kill_chain_phases": len(KillChainPhase),
        }

apt_detector = APTDetector()
