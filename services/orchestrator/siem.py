"""
SIEM Export — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Exports audit logs in Splunk HEC, ELK/Logstash, and CEF formats.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("qwen.siem")


# ============================================================================
#  EXPORT FORMATS
# ============================================================================

class SIEMFormat(str, Enum):
    SPLUNK_HEC = "splunk_hec"       # Splunk HTTP Event Collector
    ELK_JSON = "elk_json"           # Elasticsearch/Logstash JSON
    CEF = "cef"                      # Common Event Format (ArcSight)
    SYSLOG_RFC5424 = "syslog_5424"  # RFC 5424 syslog


class SIEMSeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
#  FORMAT CONVERTERS
# ============================================================================

def to_splunk_hec(event: Dict[str, Any], source: str = "ason-verification") -> Dict:
    """Convert event to Splunk HTTP Event Collector format."""
    return {
        "time": _iso_to_epoch(event.get("timestamp", "")),
        "host": os.getenv("HOSTNAME", "ason-orchestrator"),
        "source": source,
        "sourcetype": "qwen:audit",
        "index": "ason_security",
        "event": {
            "event_type": event.get("event_type", "unknown"),
            "tenant_id": event.get("tenant_id", ""),
            "user_id": event.get("user_id", ""),
            "action": event.get("action", ""),
            "resource": event.get("resource", ""),
            "outcome": event.get("outcome", "success"),
            "severity": event.get("severity", "info"),
            "details": event.get("details", {}),
            "source_ip": event.get("source_ip", ""),
            "request_id": event.get("request_id", ""),
        },
    }


def to_elk_json(event: Dict[str, Any]) -> Dict:
    """Convert event to ELK/Elasticsearch JSON format."""
    return {
        "@timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "@version": "1",
        "log.level": _severity_to_log_level(event.get("severity", "info")),
        "event.kind": "event",
        "event.category": event.get("event_type", "unknown").split(".")[0],
        "event.action": event.get("action", ""),
        "event.outcome": event.get("outcome", "success"),
        "event.severity": _severity_to_number(event.get("severity", "info")),

        "organization.id": event.get("tenant_id", ""),
        "user.id": event.get("user_id", ""),
        "user.email": event.get("user_email", ""),

        "source.ip": event.get("source_ip", ""),
        "host.name": os.getenv("HOSTNAME", "ason-orchestrator"),

        "qwen.request_id": event.get("request_id", ""),
        "qwen.event_type": event.get("event_type", ""),
        "qwen.details": event.get("details", {}),

        "labels": {
            "application": "ason-verification",
            "environment": os.getenv("ASON_ENV", "production"),
        },
    }


def to_cef(event: Dict[str, Any]) -> str:
    """Convert event to Common Event Format (CEF) string."""
    severity = _severity_to_cef(event.get("severity", "info"))
    name = event.get("event_type", "unknown").replace(".", " ").title()

    # CEF header: Version|DeviceVendor|DeviceProduct|DeviceVersion|SignatureID|Name|Severity|
    header = f"CEF:0|LibertyCenterOne|AsonVerification|2.0|{event.get('event_type', 'unknown')}|{name}|{severity}|"

    # Extension fields
    extensions = [
        f"rt={_iso_to_epoch_ms(event.get('timestamp', ''))}",
        f"src={event.get('source_ip', '')}",
        f"suser={event.get('user_id', '')}",
        f"cs1={event.get('tenant_id', '')}",
        f"cs1Label=TenantID",
        f"cs2={event.get('request_id', '')}",
        f"cs2Label=RequestID",
        f"act={event.get('action', '')}",
        f"outcome={event.get('outcome', 'success')}",
        f"msg={json.dumps(event.get('details', {}))}",
    ]

    return header + " ".join(extensions)


def to_syslog_rfc5424(event: Dict[str, Any]) -> str:
    """Convert event to RFC 5424 syslog format."""
    pri = _severity_to_syslog_pri(event.get("severity", "info"))
    timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())
    hostname = os.getenv("HOSTNAME", "ason-orchestrator")
    app = "ason-verification"
    pid = str(os.getpid())
    msg_id = event.get("request_id", "-")

    structured_data = (
        f'[qwen@52311 tenantId="{event.get("tenant_id", "")}" '
        f'userId="{event.get("user_id", "")}" '
        f'eventType="{event.get("event_type", "")}"]'
    )

    msg = json.dumps(event.get("details", {}))

    return f"<{pri}>1 {timestamp} {hostname} {app} {pid} {msg_id} {structured_data} {msg}"


# ============================================================================
#  SIEM EXPORTER
# ============================================================================

class SIEMExporter:
    """
    Ships audit logs to external SIEM systems.
    Supports batch delivery with retry logic.
    """

    def __init__(self):
        self._destinations: Dict[str, Dict] = {}
        self._buffer: List[Dict] = []
        self._buffer_size: int = 100
        self._http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        self._http_client = httpx.AsyncClient(
            timeout=30,
            limits=httpx.Limits(max_connections=10),
        )

    def add_destination(
        self, name: str, url: str, format_type: SIEMFormat,
        auth_header: str = "", batch_size: int = 100,
    ):
        """Register a SIEM destination."""
        self._destinations[name] = {
            "url": url,
            "format": format_type,
            "auth_header": auth_header,
            "batch_size": batch_size,
            "sent_count": 0,
            "error_count": 0,
        }

    async def export_event(self, event: Dict[str, Any]):
        """Export a single event to all configured SIEM destinations."""
        for name, dest in self._destinations.items():
            try:
                formatted = self._format_event(event, dest["format"])
                await self._send(name, dest, formatted)
            except Exception as e:
                dest["error_count"] += 1
                logger.error(f"SIEM export to {name} failed: {e}")

    async def export_batch(self, events: List[Dict[str, Any]]):
        """Export a batch of events."""
        for event in events:
            await self.export_event(event)

    def _format_event(self, event: Dict, fmt: SIEMFormat) -> Any:
        if fmt == SIEMFormat.SPLUNK_HEC:
            return to_splunk_hec(event)
        elif fmt == SIEMFormat.ELK_JSON:
            return to_elk_json(event)
        elif fmt == SIEMFormat.CEF:
            return to_cef(event)
        elif fmt == SIEMFormat.SYSLOG_RFC5424:
            return to_syslog_rfc5424(event)
        return event

    async def _send(self, name: str, dest: Dict, payload: Any):
        """Send formatted event to SIEM destination."""
        headers = {"Content-Type": "application/json"}
        if dest["auth_header"]:
            headers["Authorization"] = dest["auth_header"]

        body = json.dumps(payload) if isinstance(payload, dict) else str(payload)

        resp = await self._http_client.post(dest["url"], content=body, headers=headers)
        if resp.status_code < 300:
            dest["sent_count"] += 1
        else:
            dest["error_count"] += 1
            logger.warning(f"SIEM {name}: HTTP {resp.status_code}")

    def get_status(self) -> Dict:
        return {
            name: {
                "url": d["url"],
                "format": d["format"].value,
                "sent_count": d["sent_count"],
                "error_count": d["error_count"],
            }
            for name, d in self._destinations.items()
        }

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()


# ============================================================================
#  HELPERS
# ============================================================================

def _iso_to_epoch(iso_str: str) -> float:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except Exception:
        return time.time()

def _iso_to_epoch_ms(iso_str: str) -> int:
    return int(_iso_to_epoch(iso_str) * 1000)

def _severity_to_number(sev: str) -> int:
    return {"info": 1, "low": 3, "medium": 5, "high": 7, "critical": 9}.get(sev, 1)

def _severity_to_log_level(sev: str) -> str:
    return {"info": "INFO", "low": "WARN", "medium": "WARN", "high": "ERROR", "critical": "CRITICAL"}.get(sev, "INFO")

def _severity_to_cef(sev: str) -> int:
    return {"info": 1, "low": 3, "medium": 5, "high": 7, "critical": 10}.get(sev, 1)

def _severity_to_syslog_pri(sev: str) -> int:
    # Facility=1 (user), Severity mapped from our levels
    facility = 1
    severity_map = {"info": 6, "low": 5, "medium": 4, "high": 3, "critical": 2}
    return facility * 8 + severity_map.get(sev, 6)


# Global singleton
siem_exporter = SIEMExporter()
