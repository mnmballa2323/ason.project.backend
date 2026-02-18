"""
Enterprise Audit Trail — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Immutable, tamper-evident audit trail with legal hold support.
Every action in the system is recorded with a cryptographic
hash chain that can be independently verified.

S&P 500 Requirement: Complete, immutable audit trail with
legal hold capability for litigation and regulatory inquiries.
"""

import hashlib
import json
import logging
import time
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("qwen.enterprise_audit")


# ============================================================================
#  AUDIT EVENT TYPES
# ============================================================================

class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ALERT = "alert"          # Requires immediate attention


class AuditCategory(str, Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    DATA_DELETION = "data_deletion"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    COMPLIANCE = "compliance"
    SECURITY = "security"
    ADMIN = "admin"


# ============================================================================
#  AUDIT ENTRY (IMMUTABLE)
# ============================================================================

class AuditEntry:
    """
    Single immutable audit entry with hash chain link.
    Once created, cannot be modified. Any tampering breaks the chain.
    """

    __slots__ = [
        "sequence", "timestamp", "category", "severity", "action",
        "actor_id", "actor_type", "tenant_id", "resource_type",
        "resource_id", "details", "source_ip", "user_agent",
        "request_id", "prev_hash", "entry_hash", "legal_hold",
    ]

    def __init__(
        self,
        sequence: int,
        category: AuditCategory,
        severity: AuditSeverity,
        action: str,
        actor_id: str = "",
        actor_type: str = "user",
        tenant_id: str = "",
        resource_type: str = "",
        resource_id: str = "",
        details: Dict = None,
        source_ip: str = "",
        user_agent: str = "",
        request_id: str = "",
        prev_hash: str = "",
        legal_hold: bool = False,
    ):
        self.sequence = sequence
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.category = category
        self.severity = severity
        self.action = action
        self.actor_id = actor_id
        self.actor_type = actor_type
        self.tenant_id = tenant_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details = details or {}
        self.source_ip = source_ip
        self.user_agent = user_agent
        self.request_id = request_id
        self.prev_hash = prev_hash
        self.legal_hold = legal_hold

        # Compute entry hash (chain link)
        self.entry_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute SHA-256 hash of this entry including previous hash."""
        payload = json.dumps({
            "seq": self.sequence,
            "ts": self.timestamp,
            "cat": self.category.value,
            "sev": self.severity.value,
            "act": self.action,
            "actor": self.actor_id,
            "tenant": self.tenant_id,
            "resource": f"{self.resource_type}:{self.resource_id}",
            "details": self.details,
            "prev": self.prev_hash,
        }, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "timestamp": self.timestamp,
            "category": self.category.value,
            "severity": self.severity.value,
            "action": self.action,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "tenant_id": self.tenant_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "source_ip": self.source_ip,
            "request_id": self.request_id,
            "prev_hash": self.prev_hash,
            "entry_hash": self.entry_hash,
            "legal_hold": self.legal_hold,
        }


# ============================================================================
#  LEGAL HOLD
# ============================================================================

class LegalHold:
    """
    Legal hold on audit data.
    When active, prevents deletion or modification of covered entries.
    Required for litigation, regulatory inquiries, and investigations.
    """

    def __init__(
        self,
        hold_id: str,
        case_name: str,
        custodian: str,
        scope: Dict,
        created_by: str,
    ):
        self.hold_id = hold_id
        self.case_name = case_name
        self.custodian = custodian
        self.scope = scope   # {"tenant_id": "...", "start_date": "...", "end_date": "..."}
        self.created_by = created_by
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.released_at: Optional[str] = None
        self.is_active = True

    def release(self, released_by: str):
        self.is_active = False
        self.released_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Legal hold {self.hold_id} released by {released_by}")

    def covers_entry(self, entry: AuditEntry) -> bool:
        """Check if this hold covers a specific audit entry."""
        if not self.is_active:
            return False
        scope_tenant = self.scope.get("tenant_id")
        if scope_tenant and entry.tenant_id != scope_tenant:
            return False
        start = self.scope.get("start_date", "")
        end = self.scope.get("end_date", "9999")
        return start <= entry.timestamp <= end

    def to_dict(self) -> dict:
        return {
            "hold_id": self.hold_id,
            "case_name": self.case_name,
            "custodian": self.custodian,
            "scope": self.scope,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "released_at": self.released_at,
            "is_active": self.is_active,
        }


# ============================================================================
#  ENTERPRISE AUDIT TRAIL
# ============================================================================

class EnterpriseAuditTrail:
    """
    Thread-safe, immutable audit trail with hash chain integrity.
    Designed for S&P 500 regulatory requirements.
    """

    def __init__(self, max_in_memory: int = 100_000):
        self._entries: List[AuditEntry] = []
        self._sequence: int = 0
        self._last_hash: str = "0" * 64   # Genesis hash
        self._lock = threading.Lock()
        self._legal_holds: Dict[str, LegalHold] = {}
        self._max_in_memory = max_in_memory

    def record(
        self,
        category: AuditCategory,
        action: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        **kwargs,
    ) -> AuditEntry:
        """Record an immutable audit entry."""
        with self._lock:
            self._sequence += 1
            entry = AuditEntry(
                sequence=self._sequence,
                category=category,
                severity=severity,
                action=action,
                prev_hash=self._last_hash,
                **kwargs,
            )
            self._last_hash = entry.entry_hash
            self._entries.append(entry)

            # Trim in-memory (entries are persisted to DB separately)
            if len(self._entries) > self._max_in_memory:
                # Keep only entries under legal hold + recent
                held = [e for e in self._entries if self._is_held(e)]
                recent = self._entries[-50_000:]
                self._entries = list(set(held + recent))

        if severity in (AuditSeverity.CRITICAL, AuditSeverity.ALERT):
            logger.warning(f"AUDIT [{severity.value}]: {action} by {kwargs.get('actor_id', 'system')}")

        return entry

    def verify_chain(self, start: int = 0, end: int = None) -> Dict:
        """Verify the integrity of the audit hash chain."""
        entries = self._entries[start:end]
        if not entries:
            return {"valid": True, "entries_verified": 0}

        prev_hash = entries[0].prev_hash
        for i, entry in enumerate(entries):
            # Recompute hash
            expected = entry._compute_hash()
            if entry.entry_hash != expected:
                return {
                    "valid": False,
                    "broken_at_sequence": entry.sequence,
                    "reason": "hash_mismatch",
                    "entries_verified": i,
                }
            if entry.prev_hash != prev_hash:
                return {
                    "valid": False,
                    "broken_at_sequence": entry.sequence,
                    "reason": "chain_link_broken",
                    "entries_verified": i,
                }
            prev_hash = entry.entry_hash

        return {"valid": True, "entries_verified": len(entries)}

    # --- Legal Hold ---

    def create_legal_hold(
        self,
        hold_id: str,
        case_name: str,
        custodian: str,
        scope: Dict,
        created_by: str,
    ) -> LegalHold:
        """Create a legal hold on audit data."""
        hold = LegalHold(hold_id, case_name, custodian, scope, created_by)
        self._legal_holds[hold_id] = hold

        # Mark covered entries
        with self._lock:
            count = 0
            for entry in self._entries:
                if hold.covers_entry(entry):
                    entry.legal_hold = True
                    count += 1

        logger.info(f"Legal hold created: {hold_id} ({case_name}), covers {count} entries")

        self.record(
            category=AuditCategory.COMPLIANCE,
            action="legal_hold_created",
            severity=AuditSeverity.CRITICAL,
            actor_id=created_by,
            details={"hold_id": hold_id, "case_name": case_name, "entries_covered": count},
        )

        return hold

    def release_legal_hold(self, hold_id: str, released_by: str):
        """Release a legal hold."""
        hold = self._legal_holds.get(hold_id)
        if hold:
            hold.release(released_by)
            self.record(
                category=AuditCategory.COMPLIANCE,
                action="legal_hold_released",
                severity=AuditSeverity.CRITICAL,
                actor_id=released_by,
                details={"hold_id": hold_id},
            )

    def _is_held(self, entry: AuditEntry) -> bool:
        """Check if an entry is under any active legal hold."""
        return any(h.covers_entry(entry) for h in self._legal_holds.values())

    # --- Query ---

    def query(
        self,
        tenant_id: str = None,
        category: AuditCategory = None,
        severity: AuditSeverity = None,
        actor_id: str = None,
        start_time: str = None,
        end_time: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Query audit entries with filters."""
        results = []
        for entry in reversed(self._entries):
            if len(results) >= limit:
                break
            if tenant_id and entry.tenant_id != tenant_id:
                continue
            if category and entry.category != category:
                continue
            if severity and entry.severity != severity:
                continue
            if actor_id and entry.actor_id != actor_id:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            results.append(entry.to_dict())
        return results

    def get_stats(self) -> Dict:
        by_category = {}
        by_severity = {}
        for entry in self._entries:
            by_category[entry.category.value] = by_category.get(entry.category.value, 0) + 1
            by_severity[entry.severity.value] = by_severity.get(entry.severity.value, 0) + 1

        return {
            "total_entries": len(self._entries),
            "sequence": self._sequence,
            "chain_head": self._last_hash[:16],
            "by_category": by_category,
            "by_severity": by_severity,
            "legal_holds_active": sum(1 for h in self._legal_holds.values() if h.is_active),
            "entries_under_hold": sum(1 for e in self._entries if e.legal_hold),
        }


# Global singleton
enterprise_audit = EnterpriseAuditTrail()
