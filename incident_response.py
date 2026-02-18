"""
Incident Response Framework — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

NIST SP 800-61 Rev. 2 aligned incident response lifecycle:
  Preparation → Detection → Containment → Eradication → Recovery → Lessons Learned

S&P 500 Requirement: Formal incident response process with SLA-based
severity classification, escalation procedures, and post-incident review.
"""

import hashlib
import json
import logging
import time
import threading
from datetime import datetime, timezone
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("qwen.incident_response")


# ============================================================================
#  SEVERITY & CLASSIFICATION
# ============================================================================

class IncidentSeverity(IntEnum):
    """Severity levels per NIST / ITIL classification."""
    SEV1_CRITICAL = 1    # Full outage, data breach, regulatory impact
    SEV2_HIGH = 2        # Major degradation, security incident
    SEV3_MEDIUM = 3      # Partial degradation, minor security event
    SEV4_LOW = 4         # Cosmetic, informational


class IncidentPhase(str, Enum):
    """NIST SP 800-61 lifecycle phases."""
    DETECTION = "detection"
    TRIAGE = "triage"
    CONTAINMENT = "containment"
    ERADICATION = "eradication"
    RECOVERY = "recovery"
    POST_INCIDENT = "post_incident"
    CLOSED = "closed"


class IncidentCategory(str, Enum):
    SECURITY_BREACH = "security_breach"
    DATA_EXPOSURE = "data_exposure"
    SERVICE_OUTAGE = "service_outage"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    COMPLIANCE_VIOLATION = "compliance_violation"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    MALWARE = "malware"
    INSIDER_THREAT = "insider_threat"
    CONFIGURATION_ERROR = "configuration_error"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"


# SLA response times (minutes) by severity
RESPONSE_SLA = {
    IncidentSeverity.SEV1_CRITICAL: {"acknowledge": 5, "respond": 15, "update_frequency": 30, "resolve_target": 240},
    IncidentSeverity.SEV2_HIGH: {"acknowledge": 15, "respond": 60, "update_frequency": 60, "resolve_target": 480},
    IncidentSeverity.SEV3_MEDIUM: {"acknowledge": 60, "respond": 240, "update_frequency": 240, "resolve_target": 2880},
    IncidentSeverity.SEV4_LOW: {"acknowledge": 480, "respond": 1440, "update_frequency": 1440, "resolve_target": 10080},
}


# ============================================================================
#  INCIDENT MODEL
# ============================================================================

class Incident:
    """A single incident with full lifecycle tracking."""

    def __init__(
        self,
        incident_id: str,
        title: str,
        description: str,
        severity: IncidentSeverity,
        category: IncidentCategory,
        reporter: str,
        tenant_id: str = "",
        affected_components: List[str] = None,
    ):
        self.incident_id = incident_id
        self.title = title
        self.description = description
        self.severity = severity
        self.category = category
        self.reporter = reporter
        self.tenant_id = tenant_id
        self.affected_components = affected_components or []

        self.phase = IncidentPhase.DETECTION
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.acknowledged_at: Optional[str] = None
        self.contained_at: Optional[str] = None
        self.resolved_at: Optional[str] = None
        self.closed_at: Optional[str] = None

        self.commander: str = ""      # Incident commander
        self.assignees: List[str] = []
        self.timeline: List[Dict] = []
        self.actions_taken: List[Dict] = []
        self.root_cause: str = ""
        self.lessons_learned: List[str] = []
        self.remediation_items: List[Dict] = []

        self.sla = RESPONSE_SLA.get(severity, RESPONSE_SLA[IncidentSeverity.SEV4_LOW])
        self.sla_breached = False

        self._add_timeline("Incident created", reporter)

    def _add_timeline(self, event: str, actor: str = "system", details: Dict = None):
        self.timeline.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "actor": actor,
            "details": details or {},
        })

    def acknowledge(self, commander: str):
        """Acknowledge the incident and assign a commander."""
        self.acknowledged_at = datetime.now(timezone.utc).isoformat()
        self.commander = commander
        self.phase = IncidentPhase.TRIAGE
        self._add_timeline(f"Acknowledged by {commander}", commander)

    def assign(self, assignee: str, role: str = "responder"):
        self.assignees.append(assignee)
        self._add_timeline(f"Assigned {assignee} as {role}", self.commander)

    def escalate(self, new_severity: IncidentSeverity, reason: str, escalated_by: str):
        """Escalate incident severity."""
        old = self.severity
        self.severity = new_severity
        self.sla = RESPONSE_SLA.get(new_severity, self.sla)
        self._add_timeline(
            f"Escalated from SEV{old.value} to SEV{new_severity.value}: {reason}",
            escalated_by,
        )
        logger.warning(f"Incident {self.incident_id} escalated to SEV{new_severity.value}")

    def contain(self, actions: List[str], actor: str):
        """Mark containment phase with actions taken."""
        self.phase = IncidentPhase.CONTAINMENT
        self.contained_at = datetime.now(timezone.utc).isoformat()
        for action in actions:
            self.actions_taken.append({
                "phase": "containment",
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
            })
        self._add_timeline(f"Contained — {len(actions)} actions taken", actor)

    def eradicate(self, root_cause: str, actions: List[str], actor: str):
        """Mark eradication phase."""
        self.phase = IncidentPhase.ERADICATION
        self.root_cause = root_cause
        for action in actions:
            self.actions_taken.append({
                "phase": "eradication",
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
            })
        self._add_timeline(f"Eradicated — root cause: {root_cause}", actor)

    def recover(self, verification_steps: List[str], actor: str):
        """Mark recovery phase."""
        self.phase = IncidentPhase.RECOVERY
        self.resolved_at = datetime.now(timezone.utc).isoformat()
        for step in verification_steps:
            self.actions_taken.append({
                "phase": "recovery",
                "action": step,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": actor,
            })
        self._add_timeline(f"Recovered — {len(verification_steps)} verification steps", actor)

    def post_incident_review(self, lessons: List[str], remediation: List[Dict], actor: str):
        """Complete post-incident review (blameless)."""
        self.phase = IncidentPhase.POST_INCIDENT
        self.lessons_learned = lessons
        self.remediation_items = remediation
        self._add_timeline(f"Post-incident review completed — {len(lessons)} lessons", actor)

    def close(self, actor: str):
        self.phase = IncidentPhase.CLOSED
        self.closed_at = datetime.now(timezone.utc).isoformat()
        self._add_timeline("Incident closed", actor)

    def to_dict(self) -> dict:
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "severity": f"SEV{self.severity.value}",
            "category": self.category.value,
            "phase": self.phase.value,
            "reporter": self.reporter,
            "commander": self.commander,
            "tenant_id": self.tenant_id,
            "affected_components": self.affected_components,
            "created_at": self.created_at,
            "acknowledged_at": self.acknowledged_at,
            "contained_at": self.contained_at,
            "resolved_at": self.resolved_at,
            "closed_at": self.closed_at,
            "root_cause": self.root_cause,
            "sla": self.sla,
            "sla_breached": self.sla_breached,
            "timeline_entries": len(self.timeline),
            "actions_taken": len(self.actions_taken),
            "lessons_learned": len(self.lessons_learned),
            "remediation_items": len(self.remediation_items),
        }


# ============================================================================
#  INCIDENT MANAGER
# ============================================================================

class IncidentManager:
    """
    Manages the full lifecycle of incidents.
    Thread-safe, local-only, zero external dependencies.
    """

    def __init__(self):
        self._incidents: Dict[str, Incident] = {}
        self._lock = threading.Lock()
        self._counter = 0
        self._on_create_hooks: List[Callable] = []

    def create(
        self,
        title: str,
        description: str,
        severity: IncidentSeverity,
        category: IncidentCategory,
        reporter: str,
        **kwargs,
    ) -> Incident:
        """Create a new incident."""
        with self._lock:
            self._counter += 1
            incident_id = f"INC-{self._counter:06d}"

        incident = Incident(
            incident_id=incident_id,
            title=title,
            description=description,
            severity=severity,
            category=category,
            reporter=reporter,
            **kwargs,
        )

        self._incidents[incident_id] = incident
        logger.warning(f"Incident created: {incident_id} — SEV{severity.value} — {title}")

        for hook in self._on_create_hooks:
            try:
                hook(incident)
            except Exception as e:
                logger.error(f"Incident hook error: {e}")

        return incident

    def get(self, incident_id: str) -> Optional[Incident]:
        return self._incidents.get(incident_id)

    def list_open(self) -> List[Dict]:
        return [i.to_dict() for i in self._incidents.values() if i.phase != IncidentPhase.CLOSED]

    def get_metrics(self) -> Dict:
        open_incidents = [i for i in self._incidents.values() if i.phase != IncidentPhase.CLOSED]
        closed = [i for i in self._incidents.values() if i.phase == IncidentPhase.CLOSED]

        by_severity = {}
        for i in open_incidents:
            key = f"SEV{i.severity.value}"
            by_severity[key] = by_severity.get(key, 0) + 1

        # MTTR (Mean Time To Resolve) for closed incidents
        resolve_times = []
        for i in closed:
            if i.created_at and i.resolved_at:
                try:
                    created = datetime.fromisoformat(i.created_at)
                    resolved = datetime.fromisoformat(i.resolved_at)
                    resolve_times.append((resolved - created).total_seconds() / 60)
                except Exception:
                    pass

        mttr = round(sum(resolve_times) / len(resolve_times), 1) if resolve_times else 0

        return {
            "total": len(self._incidents),
            "open": len(open_incidents),
            "closed": len(closed),
            "by_severity": by_severity,
            "mttr_minutes": mttr,
            "sla_breaches": sum(1 for i in self._incidents.values() if i.sla_breached),
        }

    def on_create(self, hook: Callable):
        self._on_create_hooks.append(hook)


# Global singleton
incident_manager = IncidentManager()
