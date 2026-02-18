"""
Change Management Engine — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

ITIL-aligned change management with approval workflows,
CAB (Change Advisory Board) review, and audit trail.

S&P 500 Requirement: All production changes must follow a
formal approval process with segregation of duties.
SOX Section 404 requirement for change management controls.
"""

import hashlib
import json
import logging
import time
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("qwen.change_management")


# ============================================================================
#  CHANGE TYPES & RISK
# ============================================================================

class ChangeType(str, Enum):
    STANDARD = "standard"       # Pre-approved, low-risk, routine
    NORMAL = "normal"           # Requires CAB approval
    EMERGENCY = "emergency"     # Urgent, post-hoc approval
    MAJOR = "major"             # Significant impact, requires VP+ approval


class ChangeRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    IMPLEMENTING = "implementing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ApprovalLevel(str, Enum):
    PEER = "peer"                    # Peer engineer review
    TEAM_LEAD = "team_lead"          # Team lead approval
    CAB = "cab"                      # Change Advisory Board
    VP_ENGINEERING = "vp_engineering" # VP-level for major changes
    CISO = "ciso"                    # CISO for security-related changes


# Required approvals by change type
APPROVAL_MATRIX = {
    ChangeType.STANDARD: [ApprovalLevel.PEER],
    ChangeType.NORMAL: [ApprovalLevel.PEER, ApprovalLevel.TEAM_LEAD, ApprovalLevel.CAB],
    ChangeType.EMERGENCY: [ApprovalLevel.TEAM_LEAD],  # Post-hoc CAB review
    ChangeType.MAJOR: [ApprovalLevel.PEER, ApprovalLevel.TEAM_LEAD, ApprovalLevel.CAB, ApprovalLevel.VP_ENGINEERING],
}


# ============================================================================
#  CHANGE REQUEST MODEL
# ============================================================================

class ChangeRequest:
    """A formal change request with approval workflow."""

    def __init__(
        self,
        change_id: str,
        title: str,
        description: str,
        change_type: ChangeType,
        risk: ChangeRisk,
        requester: str,
        tenant_id: str = "",
        affected_systems: List[str] = None,
        rollback_plan: str = "",
        test_plan: str = "",
        implementation_plan: str = "",
        scheduled_at: str = "",
        maintenance_window: str = "",
    ):
        self.change_id = change_id
        self.title = title
        self.description = description
        self.change_type = change_type
        self.risk = risk
        self.requester = requester
        self.tenant_id = tenant_id
        self.affected_systems = affected_systems or []
        self.rollback_plan = rollback_plan
        self.test_plan = test_plan
        self.implementation_plan = implementation_plan
        self.scheduled_at = scheduled_at
        self.maintenance_window = maintenance_window

        self.status = ChangeStatus.DRAFT
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.submitted_at: Optional[str] = None
        self.approved_at: Optional[str] = None
        self.implemented_at: Optional[str] = None
        self.completed_at: Optional[str] = None

        # Approval tracking
        self.required_approvals = list(APPROVAL_MATRIX.get(change_type, []))
        self.approvals: List[Dict] = []
        self.rejections: List[Dict] = []
        self.comments: List[Dict] = []

        # Implementation
        self.implementation_notes: str = ""
        self.post_implementation_review: Dict = {}
        self.rollback_executed: bool = False

    def submit(self):
        """Submit the change request for review."""
        if not self.rollback_plan:
            raise ValueError("Rollback plan is required")
        if not self.test_plan:
            raise ValueError("Test plan is required")
        self.status = ChangeStatus.SUBMITTED
        self.submitted_at = datetime.now(timezone.utc).isoformat()

    def approve(self, approver: str, level: ApprovalLevel, notes: str = ""):
        """Record an approval."""
        self.approvals.append({
            "approver": approver,
            "level": level.value,
            "notes": notes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Check if all required approvals are met
        approved_levels = {a["level"] for a in self.approvals}
        required_levels = {l.value for l in self.required_approvals}

        if required_levels.issubset(approved_levels):
            self.status = ChangeStatus.APPROVED
            self.approved_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Change {self.change_id} fully approved")

    def reject(self, rejector: str, level: ApprovalLevel, reason: str):
        """Reject the change request."""
        self.status = ChangeStatus.REJECTED
        self.rejections.append({
            "rejector": rejector,
            "level": level.value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.warning(f"Change {self.change_id} rejected by {rejector}: {reason}")

    def begin_implementation(self, implementer: str):
        """Mark implementation as started."""
        if self.status not in (ChangeStatus.APPROVED, ChangeStatus.SCHEDULED):
            raise ValueError(f"Cannot implement change in status: {self.status}")
        self.status = ChangeStatus.IMPLEMENTING
        self.implemented_at = datetime.now(timezone.utc).isoformat()

    def complete(self, notes: str = "", verification_passed: bool = True):
        """Mark change as completed."""
        if verification_passed:
            self.status = ChangeStatus.COMPLETED
        else:
            self.status = ChangeStatus.FAILED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.implementation_notes = notes

    def rollback(self, reason: str, actor: str):
        """Execute rollback."""
        self.status = ChangeStatus.ROLLED_BACK
        self.rollback_executed = True
        self.comments.append({
            "type": "rollback",
            "actor": actor,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.warning(f"Change {self.change_id} rolled back: {reason}")

    @property
    def is_fully_approved(self) -> bool:
        approved_levels = {a["level"] for a in self.approvals}
        required_levels = {l.value for l in self.required_approvals}
        return required_levels.issubset(approved_levels)

    def to_dict(self) -> dict:
        return {
            "change_id": self.change_id,
            "title": self.title,
            "type": self.change_type.value,
            "risk": self.risk.value,
            "status": self.status.value,
            "requester": self.requester,
            "affected_systems": self.affected_systems,
            "created_at": self.created_at,
            "submitted_at": self.submitted_at,
            "approved_at": self.approved_at,
            "completed_at": self.completed_at,
            "approvals": len(self.approvals),
            "required_approvals": [l.value for l in self.required_approvals],
            "is_fully_approved": self.is_fully_approved,
            "has_rollback_plan": bool(self.rollback_plan),
            "has_test_plan": bool(self.test_plan),
            "rollback_executed": self.rollback_executed,
        }


# ============================================================================
#  CHANGE MANAGEMENT ENGINE
# ============================================================================

class ChangeManagementEngine:
    """Manages the full lifecycle of change requests."""

    def __init__(self):
        self._changes: Dict[str, ChangeRequest] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def create(self, title: str, description: str, change_type: ChangeType,
               risk: ChangeRisk, requester: str, **kwargs) -> ChangeRequest:
        with self._lock:
            self._counter += 1
            change_id = f"CHG-{self._counter:06d}"

        cr = ChangeRequest(change_id, title, description, change_type, risk, requester, **kwargs)
        self._changes[change_id] = cr
        return cr

    def get(self, change_id: str) -> Optional[ChangeRequest]:
        return self._changes.get(change_id)

    def list_pending(self) -> List[Dict]:
        """List changes awaiting approval."""
        return [
            c.to_dict() for c in self._changes.values()
            if c.status in (ChangeStatus.SUBMITTED, ChangeStatus.UNDER_REVIEW)
        ]

    def get_metrics(self) -> Dict:
        total = len(self._changes)
        approved = sum(1 for c in self._changes.values() if c.status == ChangeStatus.APPROVED)
        rejected = sum(1 for c in self._changes.values() if c.status == ChangeStatus.REJECTED)
        rolled_back = sum(1 for c in self._changes.values() if c.rollback_executed)
        completed = sum(1 for c in self._changes.values() if c.status == ChangeStatus.COMPLETED)

        return {
            "total_changes": total,
            "approved": approved,
            "rejected": rejected,
            "completed": completed,
            "rolled_back": rolled_back,
            "success_rate": round(completed / max(1, completed + rolled_back) * 100, 1),
            "pending_approval": len(self.list_pending()),
        }


# Global singleton
change_engine = ChangeManagementEngine()
