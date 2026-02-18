"""
Cyber Threat Intelligence Platform — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

STIX/TAXII engine, IOC lifecycle, threat actor profiling,
campaign attribution. All local, no external threat feeds.
"""

import hashlib, logging, os, time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.ctip")


class STIXType(str, Enum):
    INDICATOR = "indicator"
    MALWARE = "malware"
    THREAT_ACTOR = "threat-actor"
    ATTACK_PATTERN = "attack-pattern"
    CAMPAIGN = "campaign"
    TOOL = "tool"
    VULNERABILITY = "vulnerability"
    IDENTITY = "identity"
    RELATIONSHIP = "relationship"


class IOCStatus(str, Enum):
    ACTIVE = "active"
    AGING = "aging"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ConfidenceLevel(str, Enum):
    HIGH = "high"         # >80%
    MEDIUM = "medium"     # 50-80%
    LOW = "low"           # <50%


class STIXObject:
    def __init__(self, stix_id, stix_type, name, description,
                 confidence=ConfidenceLevel.MEDIUM, labels=None):
        self.stix_id = stix_id
        self.stix_type = stix_type
        self.name = name
        self.description = description
        self.confidence = confidence
        self.labels = labels or []
        self.created = datetime.now(timezone.utc).isoformat()
        self.modified = self.created
        self.revoked = False
        self.relationships: List[str] = []

    def to_stix(self) -> Dict:
        return {"type": self.stix_type.value, "id": self.stix_id,
                "name": self.name, "description": self.description[:100],
                "confidence": self.confidence.value,
                "labels": self.labels, "created": self.created}


class IOCEntry:
    def __init__(self, ioc_id, pattern, pattern_type, source,
                 confidence, ttl_days=90):
        self.ioc_id = ioc_id
        self.pattern = pattern
        self.pattern_type = pattern_type
        self.source = source
        self.confidence = confidence
        self.ttl_days = ttl_days
        self.status = IOCStatus.ACTIVE
        self.created_at = datetime.now(timezone.utc)
        self.hits = 0
        self.last_seen: Optional[str] = None

    @property
    def age_days(self):
        return (datetime.now(timezone.utc) - self.created_at).days

    def to_dict(self):
        return {"id": self.ioc_id, "pattern": self.pattern[:40],
                "type": self.pattern_type, "status": self.status.value,
                "confidence": self.confidence.value,
                "hits": self.hits, "age_days": self.age_days}


class ThreatActor:
    def __init__(self, actor_id, name, aliases, nation_state,
                 sophistication, primary_motivation, ttps):
        self.actor_id = actor_id
        self.name = name
        self.aliases = aliases
        self.nation_state = nation_state
        self.sophistication = sophistication
        self.motivation = primary_motivation
        self.ttps = ttps
        self.campaigns: List[str] = []
        self.first_seen = "2020-01-01"
        self.active = True

    def to_dict(self):
        return {"id": self.actor_id, "name": self.name,
                "aliases": self.aliases, "nation": self.nation_state,
                "sophistication": self.sophistication,
                "ttps": len(self.ttps), "campaigns": len(self.campaigns)}


class Campaign:
    def __init__(self, camp_id, name, actor_id, objective,
                 first_seen, techniques):
        self.camp_id = camp_id
        self.name = name
        self.actor_id = actor_id
        self.objective = objective
        self.first_seen = first_seen
        self.techniques = techniques
        self.incidents: List[str] = []
        self.confidence = ConfidenceLevel.MEDIUM

    def to_dict(self):
        return {"id": self.camp_id, "name": self.name,
                "actor": self.actor_id, "objective": self.objective,
                "techniques": len(self.techniques),
                "incidents": len(self.incidents)}


class CyberThreatIntelPlatform:
    """Self-hosted STIX/TAXII threat intelligence."""

    def __init__(self):
        self._stix: Dict[str, STIXObject] = {}
        self._iocs: Dict[str, IOCEntry] = {}
        self._actors: Dict[str, ThreatActor] = {}
        self._campaigns: Dict[str, Campaign] = {}
        self._stix_counter = 0
        self._ioc_counter = 0
        self._seed()

    def _seed(self):
        # Known threat actors
        actors = [
            ("APT28", ["Fancy Bear", "Sofacy"], "Russia", "expert",
             "espionage", ["T1566", "T1059", "T1078", "T1027"]),
            ("APT29", ["Cozy Bear", "The Dukes"], "Russia", "expert",
             "espionage", ["T1195", "T1053", "T1071", "T1573"]),
            ("APT41", ["Winnti", "Barium"], "China", "expert",
             "financial+espionage", ["T1190", "T1068", "T1003", "T1005"]),
            ("Lazarus", ["Hidden Cobra", "ZINC"], "North Korea", "expert",
             "financial", ["T1566", "T1486", "T1059", "T1041"]),
            ("FIN7", ["Carbanak"], "unknown", "advanced",
             "financial", ["T1566", "T1059", "T1005", "T1041"]),
        ]
        for i, (name, aliases, nation, soph, motiv, ttps) in enumerate(actors, 1):
            aid = f"TA-{i:04d}"
            self._actors[aid] = ThreatActor(aid, name, aliases, nation, soph, motiv, ttps)

        # Seed IOCs
        iocs = [
            ("185.141.63.0/24", "ipv4-cidr", "APT28 C2 range"),
            ("evil-update.com", "domain", "Supply chain domain"),
            ("a3b9c8d7e6f5...", "file-hash-sha256", "Cobalt Strike beacon"),
            ("Mozilla/5.0 (compatible; MSIE 6", "user-agent", "Legacy scanner UA"),
            ("EICAR-STANDARD-ANTIVIRUS", "test-string", "AV test pattern"),
        ]
        for pattern, ptype, desc in iocs:
            self._ioc_counter += 1
            iid = f"IOC-{self._ioc_counter:08d}"
            self._iocs[iid] = IOCEntry(iid, pattern, ptype, "internal",
                                        ConfidenceLevel.HIGH)

    def add_indicator(self, pattern: str, pattern_type: str,
                      confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM) -> IOCEntry:
        self._ioc_counter += 1
        iid = f"IOC-{self._ioc_counter:08d}"
        ioc = IOCEntry(iid, pattern, pattern_type, "platform", confidence)
        self._iocs[iid] = ioc
        return ioc

    def match_ioc(self, value: str) -> List[Dict]:
        matches = []
        for ioc in self._iocs.values():
            if ioc.status == IOCStatus.ACTIVE and ioc.pattern in value:
                ioc.hits += 1
                ioc.last_seen = datetime.now(timezone.utc).isoformat()
                matches.append(ioc.to_dict())
        return matches

    def age_iocs(self):
        for ioc in self._iocs.values():
            if ioc.age_days > ioc.ttl_days:
                ioc.status = IOCStatus.EXPIRED
            elif ioc.age_days > ioc.ttl_days * 0.7:
                ioc.status = IOCStatus.AGING

    def attribute_campaign(self, incidents: List[str],
                           techniques: List[str]) -> Dict:
        """Attempt to attribute incidents to a known actor."""
        best_match = None
        best_score = 0
        for actor in self._actors.values():
            overlap = len(set(techniques) & set(actor.ttps))
            if overlap > best_score:
                best_score = overlap
                best_match = actor
        if best_match and best_score >= 2:
            return {"attributed": True, "actor": best_match.name,
                    "confidence": "medium" if best_score < 3 else "high",
                    "ttp_overlap": best_score}
        return {"attributed": False}

    def get_stats(self) -> Dict:
        return {"stix_objects": len(self._stix),
                "iocs_active": sum(1 for i in self._iocs.values()
                                   if i.status == IOCStatus.ACTIVE),
                "threat_actors": len(self._actors),
                "campaigns": len(self._campaigns)}

ctip = CyberThreatIntelPlatform()
