"""
Threat Hunting Engine — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Proactive, hypothesis-driven threat hunting with:
- YARA-style rule matching for IOC sweeps
- Behavioral hypothesis testing
- Attack technique hunting (MITRE ATT&CK TTP)
- Automated hunt playbooks

NASDAQ 100 Requirement: proactive defense, not just reactive.
"""

import hashlib
import logging
import re
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("qwen.threat_hunting")


class HuntStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"


class HuntType(str, Enum):
    HYPOTHESIS = "hypothesis"        # Analyst-driven hypothesis
    IOC_SWEEP = "ioc_sweep"          # Indicator of Compromise sweep
    TTP_HUNT = "ttp_hunt"            # MITRE TTP pattern hunting
    ANOMALY = "anomaly"              # Statistical anomaly hunting
    PLAYBOOK = "playbook"            # Automated playbook execution


class IOCType(str, Enum):
    IP_ADDRESS = "ip"
    DOMAIN = "domain"
    FILE_HASH_SHA256 = "sha256"
    FILE_HASH_MD5 = "md5"
    EMAIL = "email"
    URL = "url"
    USER_AGENT = "user_agent"
    YARA_RULE = "yara"
    REGEX = "regex"
    API_KEY_PATTERN = "api_key"


class ThreatIOC:
    """An Indicator of Compromise."""
    def __init__(self, ioc_type, value, description="",
                 severity=5, source="internal"):
        self.ioc_type = ioc_type
        self.value = value
        self.description = description
        self.severity = severity
        self.source = source
        self.added_at = datetime.now(timezone.utc).isoformat()
        self.hit_count = 0

    def matches(self, data: str) -> bool:
        if self.ioc_type == IOCType.REGEX:
            return bool(re.search(self.value, data))
        elif self.ioc_type == IOCType.FILE_HASH_SHA256:
            h = hashlib.sha256(data.encode()).hexdigest()
            return h == self.value
        else:
            return self.value.lower() in data.lower()

    def to_dict(self):
        return {
            "type": self.ioc_type.value, "value": self.value[:50],
            "severity": self.severity, "hits": self.hit_count,
            "source": self.source,
        }


class HuntHypothesis:
    """A structured threat hunting hypothesis."""
    def __init__(self, hunt_id, name, hunt_type, hypothesis,
                 data_sources, mitre_ref=""):
        self.hunt_id = hunt_id
        self.name = name
        self.hunt_type = hunt_type
        self.hypothesis = hypothesis
        self.data_sources = data_sources
        self.mitre_ref = mitre_ref
        self.status = HuntStatus.DRAFT
        self.findings: List[Dict] = []
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: Optional[str] = None
        self.analyst = ""
        self.conclusion = ""

    def add_finding(self, description, evidence, severity=5):
        self.findings.append({
            "description": description, "evidence": evidence,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def complete(self, conclusion, escalate=False):
        self.status = HuntStatus.ESCALATED if escalate else HuntStatus.COMPLETED
        self.conclusion = conclusion
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "hunt_id": self.hunt_id, "name": self.name,
            "type": self.hunt_type.value, "status": self.status.value,
            "hypothesis": self.hypothesis, "mitre_ref": self.mitre_ref,
            "findings_count": len(self.findings),
            "conclusion": self.conclusion,
        }


class ThreatHuntingEngine:
    """Proactive threat hunting with IOC sweeps and hypothesis testing."""

    def __init__(self):
        self._iocs: List[ThreatIOC] = []
        self._hunts: Dict[str, HuntHypothesis] = {}
        self._lock = threading.Lock()
        self._counter = 0
        self._register_default_iocs()
        self._register_default_hunts()

    def _register_default_iocs(self):
        """Seed IOC database with common threat indicators."""
        S = IOCType

        # Known malicious patterns
        self.add_ioc(S.REGEX, r"(?i)/etc/passwd|/etc/shadow",
                     "Unix password file access", 9)
        self.add_ioc(S.REGEX, r"(?i)AKIAI[A-Z0-9]{16}",
                     "AWS access key pattern", 8)
        self.add_ioc(S.REGEX, r"ghp_[A-Za-z0-9]{36}",
                     "GitHub personal access token", 8)
        self.add_ioc(S.REGEX, r"(?i)eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
                     "Exposed JWT token", 7)
        self.add_ioc(S.REGEX, r"(?i)(<\|im_start\|>|<\|endoftext\|>|ASSISTANT:)",
                     "LLM control token injection", 9)
        self.add_ioc(S.REGEX, r"(?i)ignore\s+(previous|all)\s+instructions",
                     "Prompt injection attempt", 9)

        # Suspicious user agents
        self.add_ioc(S.USER_AGENT, "sqlmap", "SQLMap scanner", 9)
        self.add_ioc(S.USER_AGENT, "nikto", "Nikto vulnerability scanner", 8)
        self.add_ioc(S.USER_AGENT, "nmap scripting engine", "Nmap scanner", 8)
        self.add_ioc(S.USER_AGENT, "gobuster", "Directory brute forcer", 8)
        self.add_ioc(S.USER_AGENT, "dirbuster", "DirBuster scanner", 8)
        self.add_ioc(S.USER_AGENT, "masscan", "Masscan port scanner", 8)

        # Suspicious IPs (RFC 5737 documentation ranges for canary matching)
        self.add_ioc(S.IP_ADDRESS, "198.51.100.", "TEST-NET-2 (suspicious)", 3)

    def _register_default_hunts(self):
        """Pre-configure automated hunt playbooks."""
        H = HuntHypothesis
        T = HuntType

        self._register_hunt(H(
            "HUNT-001", "Insider Data Exfiltration",
            T.HYPOTHESIS,
            "An insider is slowly exfiltrating classified verification data "
            "by accessing records outside their normal scope",
            ["audit_logs", "access_logs", "data_classification"],
            "T1567"))

        self._register_hunt(H(
            "HUNT-002", "Dormant Account Compromise",
            T.TTP_HUNT,
            "Inactive service accounts are being used for unauthorized access "
            "indicating stolen credentials",
            ["auth_logs", "account_activity"],
            "T1078"))

        self._register_hunt(H(
            "HUNT-003", "LLM Prompt Injection Campaign",
            T.TTP_HUNT,
            "Coordinated prompt injection attacks attempting to manipulate "
            "verification outcomes through adversarial inputs",
            ["verification_logs", "input_logs", "ids_alerts"],
            "Custom-PI"))

        self._register_hunt(H(
            "HUNT-004", "Supply Chain Indicator Sweep",
            T.IOC_SWEEP,
            "Sweep all dependencies and build artifacts for known "
            "supply chain compromise indicators",
            ["sbom", "build_logs", "dependency_hashes"],
            "T1195"))

        self._register_hunt(H(
            "HUNT-005", "Crypto Key Misuse Detection",
            T.ANOMALY,
            "Detect anomalous cryptographic key usage patterns that may "
            "indicate key compromise or unauthorized key copying",
            ["key_management_logs", "hsm_audit", "crypto_ops"],
            "T1552"))

    def add_ioc(self, ioc_type, value, description="", severity=5, source="internal"):
        self._iocs.append(ThreatIOC(ioc_type, value, description, severity, source))

    def _register_hunt(self, hunt: HuntHypothesis):
        self._hunts[hunt.hunt_id] = hunt

    def sweep(self, data: str, context: str = "") -> List[Dict]:
        """Sweep data against all IOCs."""
        hits = []
        for ioc in self._iocs:
            if ioc.matches(data):
                ioc.hit_count += 1
                hits.append({
                    "ioc": ioc.to_dict(),
                    "context": context,
                    "match_time": datetime.now(timezone.utc).isoformat(),
                })
        if hits:
            logger.warning(f"IOC SWEEP: {len(hits)} hits in context '{context}'")
        return hits

    def create_hunt(self, name, hunt_type, hypothesis,
                    data_sources, mitre_ref="") -> HuntHypothesis:
        with self._lock:
            self._counter += 1
            hunt_id = f"HUNT-{self._counter + 100:04d}"
        hunt = HuntHypothesis(hunt_id, name, hunt_type, hypothesis,
                              data_sources, mitre_ref)
        self._hunts[hunt_id] = hunt
        return hunt

    def execute_playbook(self, hunt_id: str) -> Dict:
        """Execute a hunt playbook."""
        hunt = self._hunts.get(hunt_id)
        if not hunt:
            return {"error": "Hunt not found"}
        hunt.status = HuntStatus.ACTIVE
        # Simulated execution — production would query real data sources
        hunt.complete(f"Hunt {hunt_id} executed — review required")
        return hunt.to_dict()

    def get_ioc_database(self) -> Dict:
        by_type = {}
        for ioc in self._iocs:
            t = ioc.ioc_type.value
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_iocs": len(self._iocs),
            "by_type": by_type,
            "total_hits": sum(i.hit_count for i in self._iocs),
            "iocs": [i.to_dict() for i in self._iocs],
        }

    def get_stats(self) -> Dict:
        return {
            "iocs_loaded": len(self._iocs),
            "hunts_total": len(self._hunts),
            "hunts_active": sum(1 for h in self._hunts.values()
                                if h.status == HuntStatus.ACTIVE),
            "hunts_escalated": sum(1 for h in self._hunts.values()
                                   if h.status == HuntStatus.ESCALATED),
            "total_findings": sum(len(h.findings) for h in self._hunts.values()),
            "hunts": [h.to_dict() for h in self._hunts.values()],
        }

threat_hunting_engine = ThreatHuntingEngine()
