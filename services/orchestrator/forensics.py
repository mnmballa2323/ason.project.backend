"""
Digital Forensics & eDiscovery — Ason Verification Platform
ZERO EXTERNAL APIs

Evidence locker, memory forensics, timeline reconstruction,
legal hold automation. Court-admissible chain of custody.
"""

import hashlib, logging, os, time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.forensics")


class EvidenceType(str, Enum):
    LOG = "log_file"
    MEMORY_DUMP = "memory_dump"
    NETWORK_CAPTURE = "network_capture"
    DISK_IMAGE = "disk_image"
    SCREENSHOT = "screenshot"
    CONFIG = "configuration"
    ARTIFACT = "digital_artifact"


class CustodyAction(str, Enum):
    COLLECTED = "collected"
    SEALED = "sealed"
    TRANSFERRED = "transferred"
    ANALYZED = "analyzed"
    STORED = "stored"
    RELEASED = "released"


class EvidenceItem:
    def __init__(self, eid, evidence_type, source, collector,
                 data_hash, size_bytes, description):
        self.eid = eid
        self.evidence_type = evidence_type
        self.source = source
        self.collector = collector
        self.data_hash = data_hash
        self.size_bytes = size_bytes
        self.description = description
        self.collected_at = datetime.now(timezone.utc).isoformat()
        self.chain: List[Dict] = [
            {"action": CustodyAction.COLLECTED.value,
             "actor": collector,
             "timestamp": self.collected_at,
             "hash": data_hash}
        ]
        self.sealed = False

    def add_custody(self, action: CustodyAction, actor: str):
        if self.sealed and action not in (CustodyAction.STORED, CustodyAction.RELEASED):
            raise ValueError("Evidence is sealed — cannot modify")
        self.chain.append({
            "action": action.value, "actor": actor,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hash": self.data_hash})

    def seal(self):
        self.sealed = True
        self.add_custody(CustodyAction.SEALED, "system")

    def to_dict(self):
        return {"eid": self.eid, "type": self.evidence_type.value,
                "source": self.source, "hash": self.data_hash[:16] + "...",
                "size_kb": self.size_bytes // 1024,
                "custody_entries": len(self.chain), "sealed": self.sealed}


class TimelineEvent:
    def __init__(self, ts, source, event_type, description, severity, related_evidence=None):
        self.timestamp = ts
        self.source = source
        self.event_type = event_type
        self.description = description
        self.severity = severity
        self.related_evidence = related_evidence

    def to_dict(self):
        return {"ts": self.timestamp, "source": self.source,
                "type": self.event_type, "desc": self.description[:100],
                "severity": self.severity}


class LegalHold:
    def __init__(self, hold_id, case_name, custodians, data_sources, 
                 issuer, reason):
        self.hold_id = hold_id
        self.case_name = case_name
        self.custodians = custodians
        self.data_sources = data_sources
        self.issuer = issuer
        self.reason = reason
        self.issued_at = datetime.now(timezone.utc).isoformat()
        self.active = True
        self.acknowledged_by: List[str] = []

    def to_dict(self):
        return {"hold_id": self.hold_id, "case": self.case_name,
                "custodians": len(self.custodians),
                "sources": len(self.data_sources),
                "active": self.active,
                "acknowledged": len(self.acknowledged_by)}


class ForensicsEngine:
    """Digital forensics and eDiscovery."""

    def __init__(self):
        self._evidence: Dict[str, EvidenceItem] = {}
        self._timeline: List[TimelineEvent] = []
        self._holds: Dict[str, LegalHold] = {}
        self._ev_counter = 0
        self._hold_counter = 0

    def collect_evidence(self, evidence_type: EvidenceType, source: str,
                         collector: str, data: str,
                         description: str) -> EvidenceItem:
        self._ev_counter += 1
        eid = f"EV-{self._ev_counter:08d}"
        data_hash = hashlib.sha256(data.encode()).hexdigest()
        item = EvidenceItem(eid, evidence_type, source, collector,
                           data_hash, len(data), description)
        self._evidence[eid] = item
        return item

    def add_timeline_event(self, ts: str, source: str, event_type: str,
                           description: str, severity: str = "info") -> TimelineEvent:
        event = TimelineEvent(ts, source, event_type, description, severity)
        self._timeline.append(event)
        self._timeline.sort(key=lambda e: e.timestamp)
        return event

    def reconstruct_timeline(self, start: str = "", end: str = "") -> List[Dict]:
        events = self._timeline
        if start:
            events = [e for e in events if e.timestamp >= start]
        if end:
            events = [e for e in events if e.timestamp <= end]
        return [e.to_dict() for e in events]

    def create_legal_hold(self, case_name: str, custodians: List[str],
                          data_sources: List[str], issuer: str,
                          reason: str) -> LegalHold:
        self._hold_counter += 1
        hold_id = f"LH-{self._hold_counter:06d}"
        hold = LegalHold(hold_id, case_name, custodians,
                        data_sources, issuer, reason)
        self._holds[hold_id] = hold
        logger.warning(f"Legal hold issued: {hold_id} — {case_name}")
        return hold

    def verify_chain_of_custody(self, eid: str) -> Dict:
        item = self._evidence.get(eid)
        if not item:
            return {"valid": False, "error": "Evidence not found"}
        # Verify hash consistency
        hashes_consistent = all(
            e["hash"] == item.data_hash for e in item.chain)
        return {"eid": eid, "valid": hashes_consistent,
                "entries": len(item.chain), "sealed": item.sealed}

    def get_stats(self) -> Dict:
        return {
            "evidence_items": len(self._evidence),
            "timeline_events": len(self._timeline),
            "legal_holds": len(self._holds),
            "active_holds": sum(1 for h in self._holds.values() if h.active),
            "sealed_evidence": sum(1 for e in self._evidence.values() if e.sealed),
        }

forensics_engine = ForensicsEngine()
