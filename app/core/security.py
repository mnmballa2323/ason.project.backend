import hashlib
import uuid
from datetime import datetime, timezone
import logging
from typing import List, Dict
from fastapi import HTTPException

logger = logging.getLogger("qwen.orchestrator")

# ============================================================================
#  RBAC — Role-Based Access Control Matrix
# ============================================================================

RBAC_MATRIX = {
    # endpoint_action -> list of allowed roles
    "submit_job": ["admin", "engineer"],
    "cancel_job": ["admin", "engineer"],
    "retry_job": ["admin", "engineer"],
    "view_status": ["admin", "engineer", "auditor"],
    "view_report": ["admin", "auditor"],
    "export_audit": ["admin", "auditor"],
    "search_audit": ["admin", "auditor"],
    "list_jobs": ["admin", "engineer", "auditor"],
    "view_templates": ["admin", "engineer", "auditor"],
    "batch_submit": ["admin", "engineer"],
    "admin_cleanup": ["admin"],
    "admin_config": ["admin"],
    "bulk_status": ["admin", "engineer", "auditor"],
}

def require_role(user: dict, action: str):
    """Enforce RBAC. Raises 403 if user lacks the required role for the action."""
    allowed = RBAC_MATRIX.get(action, [])
    user_roles = user.get("roles", [])
    if not any(r in allowed for r in user_roles):
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden. Action '{action}' requires one of: {allowed}. Your roles: {user_roles}"
        )


# ============================================================================
#  ENTERPRISE SECURITY & GOVERNANCE
# ============================================================================

class AuditLogger:
    """
    Immutable, structured logger for Compliance (ISO 27001 / GxP / IRS).
    Maintains a SHA-256 cryptographic chain of events to prevent tampering.
    """
    def __init__(self):
        self._prev_hash = "0" * 64
        self.logs: List[dict] = []

    def log(self, actor: str, action: str, target: str, status: str, details: dict = None):
        ts = datetime.now(timezone.utc).isoformat()
        current_hash = self._hash_event(actor, action, target, ts, self._prev_hash)

        event = {
            "timestamp": ts,
            "event_id": str(uuid.uuid4()),
            "actor": actor,
            "action": action,
            "target": target,
            "status": status,
            "details": details or {},
            "prev_hash": self._prev_hash,
            "integrity_hash": current_hash,
        }

        self._prev_hash = current_hash
        self.logs.append(event)
        logger.info("Audit event", extra={"audit": event})

    def _hash_event(self, actor, action, target, timestamp, prev_hash) -> str:
        """Chain integrity hash: H(n) = SHA256(Data + H(n-1))"""
        raw = f"{actor}:{action}:{target}:{timestamp}:{prev_hash}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def export_logs(self) -> dict:
        """Exports the full audit chain for regulatory review."""
        return {
            "export_timestamp": datetime.now(timezone.utc).isoformat(),
            "chain_integrity": self.verify_chain(),
            "total_events": len(self.logs),
            "events": self.logs,
        }

    def verify_chain(self) -> str:
        """Walk the chain and verify every link. Returns VALID or BROKEN."""
        prev = "0" * 64
        for event in self.logs:
            expected = self._hash_event(
                event["actor"], event["action"], event["target"],
                event["timestamp"], prev
            )
            if expected != event["integrity_hash"]:
                return f"BROKEN at event {event['event_id']}"
            prev = event["integrity_hash"]
        return "VALID"

audit_logger = AuditLogger()
