"""
Data Classification Engine — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

S&P 500 Requirement: All data must be classified according to sensitivity.
Enforces handling rules, access controls, retention, and encryption
requirements based on classification level.

Aligned with:
- NIST SP 800-60 (Guide for Mapping Types of Information)
- ISO 27001 Annex A.8.2 (Information Classification)
"""

import hashlib
import logging
import re
import time
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("qwen.classification")


# ============================================================================
#  CLASSIFICATION LEVELS (ISO 27001 aligned)
# ============================================================================

class ClassificationLevel(IntEnum):
    """Data classification levels — lower number = less sensitive."""
    PUBLIC = 1            # Publicly available information
    INTERNAL = 2          # Internal use only
    CONFIDENTIAL = 3      # Restricted to authorized personnel
    RESTRICTED = 4        # Highest sensitivity — regulatory/legal obligation


class DataCategory(str):
    """Data categories for classification rules."""
    PII = "pii"                           # Personally Identifiable Information
    PHI = "phi"                           # Protected Health Information (HIPAA)
    PCI = "pci"                           # Payment Card Data (PCI-DSS)
    FINANCIAL = "financial"               # Financial records (SOX)
    LEGAL = "legal"                       # Legal/privileged communications
    TRADE_SECRET = "trade_secret"         # Proprietary/trade secrets
    CREDENTIAL = "credential"             # Passwords, API keys, tokens
    VERIFICATION_INPUT = "verification"   # User-submitted claims
    VERIFICATION_RESULT = "result"        # Verification outputs
    AUDIT = "audit"                       # Audit trail data
    SYSTEM = "system"                     # System configuration
    TELEMETRY = "telemetry"               # Metrics, logs, traces


# ============================================================================
#  CLASSIFICATION RULES
# ============================================================================

# Category → minimum classification level
CATEGORY_CLASSIFICATION: Dict[str, ClassificationLevel] = {
    DataCategory.PII: ClassificationLevel.CONFIDENTIAL,
    DataCategory.PHI: ClassificationLevel.RESTRICTED,
    DataCategory.PCI: ClassificationLevel.RESTRICTED,
    DataCategory.FINANCIAL: ClassificationLevel.CONFIDENTIAL,
    DataCategory.LEGAL: ClassificationLevel.RESTRICTED,
    DataCategory.TRADE_SECRET: ClassificationLevel.RESTRICTED,
    DataCategory.CREDENTIAL: ClassificationLevel.RESTRICTED,
    DataCategory.VERIFICATION_INPUT: ClassificationLevel.INTERNAL,
    DataCategory.VERIFICATION_RESULT: ClassificationLevel.CONFIDENTIAL,
    DataCategory.AUDIT: ClassificationLevel.CONFIDENTIAL,
    DataCategory.SYSTEM: ClassificationLevel.INTERNAL,
    DataCategory.TELEMETRY: ClassificationLevel.INTERNAL,
}

# Classification → handling requirements
HANDLING_REQUIREMENTS: Dict[ClassificationLevel, Dict] = {
    ClassificationLevel.PUBLIC: {
        "encryption_at_rest": False,
        "encryption_in_transit": True,
        "access_logging": False,
        "retention_days": 365,
        "backup_required": False,
        "deletion_method": "standard",
        "sharing": "unrestricted",
        "label": "PUBLIC",
    },
    ClassificationLevel.INTERNAL: {
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "access_logging": True,
        "retention_days": 730,        # 2 years
        "backup_required": True,
        "deletion_method": "secure_delete",
        "sharing": "internal_only",
        "label": "INTERNAL",
    },
    ClassificationLevel.CONFIDENTIAL: {
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "access_logging": True,
        "retention_days": 2555,       # 7 years (SOX)
        "backup_required": True,
        "deletion_method": "crypto_shred",
        "sharing": "need_to_know",
        "approved_storage": ["encrypted_postgres", "encrypted_milvus"],
        "label": "CONFIDENTIAL",
    },
    ClassificationLevel.RESTRICTED: {
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "access_logging": True,
        "retention_days": 2555,       # 7 years
        "backup_required": True,
        "deletion_method": "crypto_shred_verify",
        "sharing": "explicit_approval_required",
        "approved_storage": ["encrypted_postgres"],
        "mfa_required": True,
        "audit_all_access": True,
        "label": "RESTRICTED",
    },
}

# PII detection patterns
PII_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                       # SSN
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.\w+\b"),  # Email
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # Credit card
    re.compile(r"\b\d{3}[\s.-]?\d{3}[\s.-]?\d{4}\b"),           # Phone
    re.compile(r"\b\d{5}(-\d{4})?\b"),                            # Zip code
    re.compile(r"\b(passport|driver.?s?\s*license)\s*#?\s*\w+", re.I),
    re.compile(r"\b(date\s+of\s+birth|DOB)\s*:?\s*\d", re.I),
]


# ============================================================================
#  CLASSIFICATION ENGINE
# ============================================================================

class ClassifiedData:
    """A classified data item with metadata."""

    def __init__(
        self,
        data_id: str,
        classification: ClassificationLevel,
        categories: List[str],
        tenant_id: str = "",
        owner: str = "",
    ):
        self.data_id = data_id
        self.classification = classification
        self.categories = categories
        self.tenant_id = tenant_id
        self.owner = owner
        self.classified_at = datetime.now(timezone.utc).isoformat()
        self.handling = HANDLING_REQUIREMENTS.get(classification, {})

    def to_dict(self) -> dict:
        return {
            "data_id": self.data_id,
            "classification": self.classification.name,
            "classification_level": self.classification.value,
            "categories": self.categories,
            "tenant_id": self.tenant_id,
            "owner": self.owner,
            "classified_at": self.classified_at,
            "handling_requirements": self.handling,
        }


class DataClassificationEngine:
    """
    Automated data classification engine.
    Scans content, detects sensitive data patterns, and applies
    classification labels based on detected categories.
    """

    def __init__(self):
        self._classifications: Dict[str, ClassifiedData] = {}
        self._total_classified: int = 0
        self._category_counts: Dict[str, int] = {}

    def classify(
        self,
        data_id: str,
        content: str = "",
        explicit_category: str = None,
        explicit_level: ClassificationLevel = None,
        tenant_id: str = "",
        owner: str = "",
    ) -> ClassifiedData:
        """
        Classify a data item.

        Priority:
        1. Explicit level (if provided)
        2. Category-based classification
        3. Auto-detection from content
        4. Default to INTERNAL
        """
        categories: Set[str] = set()
        max_level = ClassificationLevel.PUBLIC

        # Auto-detect from content
        if content:
            detected = self._detect_categories(content)
            categories.update(detected)

        # Add explicit category
        if explicit_category:
            categories.add(explicit_category)

        # Determine classification from categories
        for cat in categories:
            cat_level = CATEGORY_CLASSIFICATION.get(cat, ClassificationLevel.INTERNAL)
            max_level = max(max_level, cat_level)

        # Explicit level override (can only elevate, never downgrade)
        if explicit_level:
            max_level = max(max_level, explicit_level)

        # Minimum: INTERNAL for anything entering the system
        if max_level < ClassificationLevel.INTERNAL:
            max_level = ClassificationLevel.INTERNAL

        result = ClassifiedData(
            data_id=data_id,
            classification=max_level,
            categories=sorted(categories),
            tenant_id=tenant_id,
            owner=owner,
        )

        self._classifications[data_id] = result
        self._total_classified += 1
        for cat in categories:
            self._category_counts[cat] = self._category_counts.get(cat, 0) + 1

        if max_level >= ClassificationLevel.CONFIDENTIAL:
            logger.info(
                f"Data classified: {data_id} → {max_level.name} "
                f"(categories: {', '.join(categories)})"
            )

        return result

    def _detect_categories(self, content: str) -> Set[str]:
        """Auto-detect data categories from content patterns."""
        detected = set()

        # PII detection
        for pattern in PII_PATTERNS:
            if pattern.search(content):
                detected.add(DataCategory.PII)
                break

        # PHI keywords
        phi_keywords = ["diagnosis", "treatment", "patient", "prescription", "HIPAA", "medical record"]
        if any(kw.lower() in content.lower() for kw in phi_keywords):
            detected.add(DataCategory.PHI)

        # Financial keywords
        fin_keywords = ["revenue", "profit", "earnings", "balance sheet", "income statement",
                        "10-K", "10-Q", "SEC filing", "material nonpublic"]
        if any(kw.lower() in content.lower() for kw in fin_keywords):
            detected.add(DataCategory.FINANCIAL)

        # Credential patterns
        cred_patterns = [
            re.compile(r"(password|secret|api.?key|token)\s*[:=]", re.I),
            re.compile(r"-----BEGIN\s+(RSA |EC )?PRIVATE KEY-----"),
            re.compile(r"AKIA[A-Z0-9]{16}"),  # AWS access key pattern
        ]
        for pattern in cred_patterns:
            if pattern.search(content):
                detected.add(DataCategory.CREDENTIAL)
                break

        return detected

    def get_classification(self, data_id: str) -> Optional[ClassifiedData]:
        return self._classifications.get(data_id)

    def get_handling_requirements(self, data_id: str) -> Dict:
        """Get handling requirements for a data item."""
        classified = self._classifications.get(data_id)
        if not classified:
            return HANDLING_REQUIREMENTS[ClassificationLevel.INTERNAL]
        return classified.handling

    def can_share(self, data_id: str, target_context: str) -> Dict:
        """Check if data can be shared in a given context."""
        classified = self._classifications.get(data_id)
        if not classified:
            return {"allowed": False, "reason": "unclassified_data"}

        sharing = classified.handling.get("sharing", "need_to_know")
        if sharing == "unrestricted":
            return {"allowed": True, "reason": "public_data"}
        elif sharing == "internal_only":
            return {"allowed": True, "reason": "internal_sharing", "log_required": True}
        elif sharing == "need_to_know":
            return {"allowed": False, "reason": "need_to_know_basis", "approval_required": True}
        elif sharing == "explicit_approval_required":
            return {"allowed": False, "reason": "explicit_approval_required", "cab_review": True}
        return {"allowed": False, "reason": "unknown_sharing_policy"}

    def get_stats(self) -> Dict:
        level_counts = {}
        for c in self._classifications.values():
            level_counts[c.classification.name] = level_counts.get(c.classification.name, 0) + 1

        return {
            "total_classified": self._total_classified,
            "by_level": level_counts,
            "by_category": dict(self._category_counts),
        }

    def get_compliance_summary(self) -> Dict:
        """Summary for compliance audits."""
        restricted = [c for c in self._classifications.values()
                      if c.classification >= ClassificationLevel.RESTRICTED]
        confidential = [c for c in self._classifications.values()
                        if c.classification >= ClassificationLevel.CONFIDENTIAL]

        return {
            "total_items": self._total_classified,
            "restricted_count": len(restricted),
            "confidential_count": len(confidential),
            "requires_crypto_shred": len([c for c in self._classifications.values()
                                          if c.handling.get("deletion_method", "").startswith("crypto")]),
            "requires_mfa": len([c for c in self._classifications.values()
                                 if c.handling.get("mfa_required", False)]),
        }


# Global singleton
classification_engine = DataClassificationEngine()
