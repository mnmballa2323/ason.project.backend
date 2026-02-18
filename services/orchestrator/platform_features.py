"""
Platform Features — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Admin Security Console, Compliance Export, Incident War Room.
"""

import hashlib, logging, time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.platform")


# ============================================================================
#  ADMIN SECURITY CONSOLE
# ============================================================================

class ConsoleWidget:
    def __init__(self, widget_id, name, category, data_source, refresh_sec):
        self.widget_id = widget_id
        self.name = name
        self.category = category
        self.data_source = data_source
        self.refresh_sec = refresh_sec

    def to_dict(self):
        return {"id": self.widget_id, "name": self.name,
                "category": self.category, "refresh_sec": self.refresh_sec}


class AdminSecurityConsole:
    """Unified security posture dashboard."""

    def __init__(self):
        self._widgets: List[ConsoleWidget] = []
        self._seed()

    def _seed(self):
        widgets = [
            ("W-001", "Threat Level Indicator", "threat", "event_bus", 5),
            ("W-002", "Active Alerts", "alerting", "security_alerting", 10),
            ("W-003", "Compliance Score", "compliance", "security_maturity", 60),
            ("W-004", "Security Posture Grade", "posture", "dashboard_api", 30),
            ("W-005", "DLP Findings", "data_protection", "dlp", 15),
            ("W-006", "SOAR Playbook Status", "response", "soar", 10),
            ("W-007", "Containment Actions", "response", "containment", 5),
            ("W-008", "Module Health", "operations", "health_checker", 30),
            ("W-009", "Active Incidents", "incident", "soar", 5),
            ("W-010", "Crypto Operations", "crypto", "security_metrics", 15),
            ("W-011", "Event Bus Throughput", "operations", "event_bus", 10),
            ("W-012", "Audit Log Entries (24h)", "audit", "merkle_log", 60),
            ("W-013", "Edge Node Status", "infra", "edge_security", 30),
            ("W-014", "Pipeline Gate Results", "cicd", "pipeline_gate", 60),
            ("W-015", "AI Model Risk", "ai_security", "secmlops", 120),
            ("W-016", "Privacy DSAR Queue", "privacy", "privacy_engine", 300),
        ]
        for wid, name, cat, source, refresh in widgets:
            self._widgets.append(ConsoleWidget(wid, name, cat, source, refresh))

    def get_layout(self) -> Dict:
        return {
            "widgets": [w.to_dict() for w in self._widgets],
            "total": len(self._widgets),
            "categories": list(set(w.category for w in self._widgets)),
            "refresh_strategy": "websocket_push",
        }

    def get_stats(self) -> Dict:
        return {"widgets": len(self._widgets)}


# ============================================================================
#  COMPLIANCE EXPORT ENGINE
# ============================================================================

class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    PDF_BUNDLE = "pdf_bundle"


class ComplianceBundle:
    def __init__(self, bundle_id, framework, format_type, artifacts):
        self.bundle_id = bundle_id
        self.framework = framework
        self.format = format_type
        self.artifacts = artifacts
        self.generated_at = datetime.now(timezone.utc).isoformat()
        self.hash = hashlib.sha256(
            f"{bundle_id}:{framework}:{self.generated_at}".encode()
        ).hexdigest()[:16]

    def to_dict(self):
        return {"id": self.bundle_id, "framework": self.framework,
                "format": self.format.value,
                "artifacts": len(self.artifacts),
                "hash": self.hash, "generated_at": self.generated_at}


class ComplianceExportEngine:
    """One-click compliance evidence package export."""

    FRAMEWORK_ARTIFACTS = {
        "SOC_2_Type_II": [
            "trust_service_criteria.json", "control_test_results.json",
            "access_control_evidence.json", "change_management_log.json",
            "incident_response_records.json", "system_availability_report.json",
            "encryption_evidence.json", "vendor_management.json",
        ],
        "ISO_27001": [
            "annex_a_controls.json", "risk_assessment.json",
            "isms_policy.json", "internal_audit_report.json",
            "corrective_actions.json", "management_review.json",
            "business_continuity_plan.json",
        ],
        "CMMC_2_0": [
            "practice_assessment.json", "artifact_inventory.json",
            "poam.json", "ssp.json",
            "access_control_evidence.json", "audit_evidence.json",
        ],
        "GDPR": [
            "dpia_report.json", "data_processing_records.json",
            "consent_records.json", "dsar_log.json",
            "cross_border_tia.json", "breach_register.json",
        ],
        "PCI_DSS": [
            "network_diagram.json", "encryption_inventory.json",
            "access_control_list.json", "vulnerability_scan_results.json",
            "penetration_test_report.json", "log_monitoring_evidence.json",
        ],
        "NIST_CSF": [
            "csf_assessment.json", "risk_register.json",
            "gap_analysis.json", "improvement_plan.json",
        ],
    }

    def __init__(self):
        self._bundles: List[ComplianceBundle] = []
        self._counter = 0

    def export(self, framework: str,
               fmt: ExportFormat = ExportFormat.JSON) -> Dict:
        self._counter += 1
        bid = f"CEB-{self._counter:08d}"
        artifacts = self.FRAMEWORK_ARTIFACTS.get(framework, [])
        bundle = ComplianceBundle(bid, framework, fmt, artifacts)
        self._bundles.append(bundle)
        return {
            "bundle": bundle.to_dict(),
            "artifacts": artifacts,
            "download_ready": True,
        }

    def export_all(self, fmt: ExportFormat = ExportFormat.JSON) -> Dict:
        results = {}
        for framework in self.FRAMEWORK_ARTIFACTS:
            results[framework] = self.export(framework, fmt)
        return {"frameworks": len(results), "bundles": results}

    def get_stats(self) -> Dict:
        return {"bundles_exported": len(self._bundles),
                "frameworks_available": len(self.FRAMEWORK_ARTIFACTS)}


# ============================================================================
#  INCIDENT WAR ROOM
# ============================================================================

class IncidentSeverity(str, Enum):
    SEV1 = "sev1"  # Platform-wide, customer impact
    SEV2 = "sev2"  # Service degradation
    SEV3 = "sev3"  # Contained, no customer impact
    SEV4 = "sev4"  # Investigation only


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    CONTAINING = "containing"
    REMEDIATING = "remediating"
    RESOLVED = "resolved"
    POST_MORTEM = "post_mortem"


class Incident:
    def __init__(self, inc_id, title, severity, description, commander):
        self.inc_id = inc_id
        self.title = title
        self.severity = severity
        self.description = description
        self.commander = commander
        self.status = IncidentStatus.OPEN
        self.opened_at = datetime.now(timezone.utc)
        self.resolved_at: Optional[datetime] = None
        self.timeline: List[Dict] = []
        self.evidence: List[str] = []
        self.playbooks: List[str] = []
        self.affected_systems: List[str] = []

    def add_timeline(self, action: str, actor: str):
        self.timeline.append({
            "action": action, "actor": actor,
            "ts": datetime.now(timezone.utc).isoformat()})

    @property
    def duration_minutes(self):
        end = self.resolved_at or datetime.now(timezone.utc)
        return (end - self.opened_at).total_seconds() / 60

    def to_dict(self):
        return {
            "id": self.inc_id, "title": self.title,
            "severity": self.severity.value,
            "status": self.status.value,
            "commander": self.commander,
            "duration_min": round(self.duration_minutes),
            "timeline_events": len(self.timeline),
            "evidence_items": len(self.evidence),
            "opened_at": self.opened_at.isoformat(),
        }


class IncidentWarRoom:
    """Unified incident management pulling from all security modules."""

    def __init__(self):
        self._incidents: Dict[str, Incident] = {}
        self._counter = 0

    def open_incident(self, title: str, severity: IncidentSeverity,
                      description: str, commander: str) -> Incident:
        self._counter += 1
        iid = f"INC-{self._counter:08d}"
        incident = Incident(iid, title, severity, description, commander)
        incident.add_timeline("Incident opened", commander)
        self._incidents[iid] = incident
        return incident

    def update_status(self, inc_id: str, status: IncidentStatus,
                      actor: str) -> Dict:
        incident = self._incidents.get(inc_id)
        if not incident:
            return {"error": "Incident not found"}
        incident.status = status
        incident.add_timeline(f"Status → {status.value}", actor)
        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.now(timezone.utc)
        return incident.to_dict()

    def add_evidence(self, inc_id: str, evidence_ref: str) -> Dict:
        incident = self._incidents.get(inc_id)
        if not incident:
            return {"error": "Incident not found"}
        incident.evidence.append(evidence_ref)
        incident.add_timeline(f"Evidence added: {evidence_ref}", "system")
        return {"evidence_count": len(incident.evidence)}

    def get_active(self) -> List[Dict]:
        return [i.to_dict() for i in self._incidents.values()
                if i.status != IncidentStatus.RESOLVED]

    def get_stats(self) -> Dict:
        active = sum(1 for i in self._incidents.values()
                     if i.status not in (IncidentStatus.RESOLVED, IncidentStatus.POST_MORTEM))
        return {
            "total_incidents": len(self._incidents),
            "active": active,
            "by_severity": {s.value: sum(1 for i in self._incidents.values()
                                          if i.severity == s) for s in IncidentSeverity},
        }


# Singletons
admin_console = AdminSecurityConsole()
compliance_export = ComplianceExportEngine()
incident_war_room = IncidentWarRoom()
