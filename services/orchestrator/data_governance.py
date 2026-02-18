"""
Data Classification & Governance — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Automated data classification, data lineage tracking, retention engine.
"""

import hashlib, logging, math, os, re, threading, time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.data_governance")


# ============================================================================
#  DATA CLASSIFIER
# ============================================================================

class DataClassification(str, Enum):
    TOP_SECRET = "top_secret"       # Nation-state level
    RESTRICTED = "restricted"       # Board/C-suite only
    CONFIDENTIAL = "confidential"   # Internal + NDA
    INTERNAL = "internal"           # All employees
    PUBLIC = "public"               # Externally shareable


class PIIType(str, Enum):
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    EMAIL = "email"
    PHONE = "phone"
    DOB = "date_of_birth"
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    IP_ADDRESS = "ip_address"
    MEDICAL_RECORD = "medical_record"
    FINANCIAL = "financial_account"


class DataClassifier:
    """Automated data classification with regex + entropy analysis."""

    PII_PATTERNS = [
        (PIIType.SSN, r'\b\d{3}-\d{2}-\d{4}\b', DataClassification.RESTRICTED),
        (PIIType.CREDIT_CARD, r'\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6011)\d{8,12}\b',
         DataClassification.RESTRICTED),
        (PIIType.EMAIL, r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
         DataClassification.CONFIDENTIAL),
        (PIIType.PHONE, r'\b(?:\+1[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b',
         DataClassification.CONFIDENTIAL),
        (PIIType.PASSPORT, r'\b[A-Z]{1,2}\d{6,9}\b', DataClassification.RESTRICTED),
        (PIIType.IP_ADDRESS, r'\b(?:\d{1,3}\.){3}\d{1,3}\b', DataClassification.INTERNAL),
        (PIIType.FINANCIAL, r'\b\d{8,17}\b', DataClassification.CONFIDENTIAL),
    ]

    SENSITIVE_KEYWORDS = {
        DataClassification.TOP_SECRET: [
            "top secret", "ts//sci", "code word", "compartmented",
            "eyes only", "noforn", "classified"],
        DataClassification.RESTRICTED: [
            "restricted", "board only", "executive", "merger",
            "acquisition", "pre-ipo", "material nonpublic"],
        DataClassification.CONFIDENTIAL: [
            "confidential", "proprietary", "trade secret", "nda",
            "internal only", "do not distribute", "attorney-client"],
    }

    def __init__(self):
        self._classifications: List[Dict] = []
        self._scans = 0

    def classify(self, content: str, source: str = "unknown") -> Dict:
        self._scans += 1
        findings = []
        highest = DataClassification.PUBLIC

        # PII pattern matching
        for pii_type, pattern, classification in self.PII_PATTERNS:
            matches = re.findall(pattern, content)
            if matches:
                findings.append({
                    "type": pii_type.value, "count": len(matches),
                    "classification": classification.value})
                if list(DataClassification).index(classification) < list(DataClassification).index(highest):
                    highest = classification

        # Keyword matching
        content_lower = content.lower()
        for classification, keywords in self.SENSITIVE_KEYWORDS.items():
            matched = [kw for kw in keywords if kw in content_lower]
            if matched:
                findings.append({
                    "type": "keyword", "keywords": matched,
                    "classification": classification.value})
                if list(DataClassification).index(classification) < list(DataClassification).index(highest):
                    highest = classification

        # Entropy analysis for potential encrypted/encoded data
        entropy = self._calculate_entropy(content)
        if entropy > 7.5:
            findings.append({"type": "high_entropy", "entropy": round(entropy, 2),
                           "note": "Possible encrypted/encoded content"})

        result = {
            "source": source, "classification": highest.value,
            "findings": findings, "pii_count": sum(f.get("count", 0) for f in findings
                                                    if f["type"] != "keyword" and f["type"] != "high_entropy"),
            "entropy": round(entropy, 2),
            "ts": datetime.now(timezone.utc).isoformat()}
        self._classifications.append(result)
        return result

    def _calculate_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        freq = defaultdict(int)
        for c in text:
            freq[c] += 1
        length = len(text)
        return -sum((count/length) * math.log2(count/length)
                    for count in freq.values() if count > 0)

    def get_stats(self) -> Dict:
        return {"scans": self._scans,
                "classifications": len(self._classifications)}


# ============================================================================
#  DATA LINEAGE
# ============================================================================

class LineageStage(str, Enum):
    INGESTION = "ingestion"
    PROCESSING = "processing"
    TRANSFORMATION = "transformation"
    STORAGE = "storage"
    ANALYSIS = "analysis"
    SHARING = "sharing"
    EGRESS = "egress"
    DELETION = "deletion"


class LineageRecord:
    def __init__(self, data_id, stage, system, actor, details=None):
        self.data_id = data_id
        self.stage = stage
        self.system = system
        self.actor = actor
        self.details = details or {}
        self.ts = datetime.now(timezone.utc)
        self.hash = hashlib.sha256(
            f"{data_id}:{stage.value}:{system}:{self.ts.isoformat()}".encode()
        ).hexdigest()[:16]

    def to_dict(self):
        return {"data_id": self.data_id, "stage": self.stage.value,
                "system": self.system, "actor": self.actor,
                "ts": self.ts.isoformat(), "hash": self.hash}


class DataLineage:
    """Track data flow: ingestion → processing → storage → egress."""

    def __init__(self):
        self._records: Dict[str, List[LineageRecord]] = defaultdict(list)

    def record(self, data_id: str, stage: LineageStage, system: str,
               actor: str, details: Dict = None) -> Dict:
        rec = LineageRecord(data_id, stage, system, actor, details)
        self._records[data_id].append(rec)
        return rec.to_dict()

    def get_lineage(self, data_id: str) -> List[Dict]:
        records = self._records.get(data_id, [])
        return [r.to_dict() for r in sorted(records, key=lambda r: r.ts)]

    def find_by_system(self, system: str) -> List[Dict]:
        results = []
        for records in self._records.values():
            for r in records:
                if r.system == system:
                    results.append(r.to_dict())
        return results

    def verify_chain(self, data_id: str) -> Dict:
        """Verify lineage chain integrity."""
        records = self._records.get(data_id, [])
        if not records:
            return {"valid": False, "reason": "No records found"}
        for i, rec in enumerate(records[1:], 1):
            if rec.ts < records[i-1].ts:
                return {"valid": False, "reason": f"Timestamp ordering violation at step {i}"}
        return {"valid": True, "steps": len(records),
                "first_seen": records[0].ts.isoformat(),
                "last_seen": records[-1].ts.isoformat()}

    def get_stats(self) -> Dict:
        return {"data_items": len(self._records),
                "total_records": sum(len(r) for r in self._records.values())}


# ============================================================================
#  RETENTION ENGINE
# ============================================================================

class RetentionAction(str, Enum):
    RETAIN = "retain"
    ARCHIVE = "archive"
    DELETE = "delete"
    LEGAL_HOLD = "legal_hold"


class RetentionPolicy:
    def __init__(self, name, data_class, retention_days, action, legal_basis):
        self.name = name
        self.data_class = data_class
        self.retention_days = retention_days
        self.action = action
        self.legal_basis = legal_basis
        self.applied = 0

    def to_dict(self):
        return {"name": self.name, "class": self.data_class.value,
                "retention_days": self.retention_days,
                "action": self.action.value, "basis": self.legal_basis}


class RetentionEngine:
    """Policy-based data retention/deletion with legal hold support."""

    def __init__(self):
        self._policies: List[RetentionPolicy] = []
        self._holds: Dict[str, Dict] = {}
        self._deletions: List[Dict] = []
        self._seed()

    def _seed(self):
        policies = [
            ("pii_gdpr", DataClassification.RESTRICTED, 365,
             RetentionAction.DELETE, "GDPR Art. 17 Right to Erasure"),
            ("financial_sox", DataClassification.CONFIDENTIAL, 2555,
             RetentionAction.ARCHIVE, "SOX Act 7-year retention"),
            ("audit_logs", DataClassification.INTERNAL, 1825,
             RetentionAction.ARCHIVE, "SOC 2 audit log requirement"),
            ("security_events", DataClassification.CONFIDENTIAL, 730,
             RetentionAction.ARCHIVE, "NIST incident response"),
            ("public_content", DataClassification.PUBLIC, 90,
             RetentionAction.DELETE, "Data minimization"),
            ("top_secret", DataClassification.TOP_SECRET, 3650,
             RetentionAction.RETAIN, "National security"),
            ("medical_hipaa", DataClassification.RESTRICTED, 2190,
             RetentionAction.ARCHIVE, "HIPAA 6-year requirement"),
            ("employee_data", DataClassification.CONFIDENTIAL, 1095,
             RetentionAction.DELETE, "Employment law 3-year"),
        ]
        for name, dclass, days, action, basis in policies:
            self._policies.append(RetentionPolicy(name, dclass, days, action, basis))

    def apply_policy(self, data_id: str, data_class: DataClassification,
                    created_at: datetime = None) -> Dict:
        if data_id in self._holds:
            return {"action": "legal_hold", "data_id": data_id,
                    "reason": "Data under legal hold — cannot delete"}
        policy = next((p for p in self._policies if p.data_class == data_class), None)
        if not policy:
            return {"action": "retain", "reason": "No matching policy"}
        created = created_at or datetime.now(timezone.utc)
        age_days = (datetime.now(timezone.utc) - created).days
        if age_days >= policy.retention_days:
            policy.applied += 1
            action = {"action": policy.action.value, "data_id": data_id,
                     "age_days": age_days, "policy": policy.name}
            if policy.action == RetentionAction.DELETE:
                self._deletions.append(action)
            return action
        return {"action": "retain", "days_until_action": policy.retention_days - age_days}

    def place_legal_hold(self, data_id: str, case_id: str, reason: str) -> Dict:
        self._holds[data_id] = {
            "case_id": case_id, "reason": reason,
            "placed_at": datetime.now(timezone.utc).isoformat()}
        return {"hold_placed": True, "data_id": data_id, "case": case_id}

    def release_hold(self, data_id: str) -> Dict:
        if data_id in self._holds:
            del self._holds[data_id]
            return {"released": True}
        return {"error": "No hold found"}

    def get_stats(self) -> Dict:
        return {"policies": len(self._policies), "holds": len(self._holds),
                "deletions": len(self._deletions)}


# Singletons
data_classifier = DataClassifier()
data_lineage = DataLineage()
retention_engine = RetentionEngine()
