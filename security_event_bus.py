"""
Security Event Bus — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Internal event bus for cross-module security event propagation.
DLP finding → SOAR playbook → containment → forensics chain.
"""

import hashlib, logging, threading, time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("qwen.event_bus")


class EventSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class EventCategory(str, Enum):
    THREAT_DETECTED = "threat_detected"
    POLICY_VIOLATION = "policy_violation"
    DATA_LEAK = "data_leak"
    AUTH_FAILURE = "auth_failure"
    CONTAINMENT = "containment_action"
    COMPLIANCE = "compliance_event"
    SYSTEM = "system_event"
    FORENSICS = "forensics_event"
    INCIDENT = "incident"
    AUDIT = "audit_event"


class SecurityEvent:
    """An event flowing through the security event bus."""

    def __init__(self, event_id: str, category: EventCategory,
                 severity: EventSeverity, source: str,
                 description: str, data: Optional[Dict] = None):
        self.event_id = event_id
        self.category = category
        self.severity = severity
        self.source = source
        self.description = description
        self.data = data or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.processed_by: List[str] = []
        self.propagated = False

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "source": self.source,
            "description": self.description[:100],
            "timestamp": self.timestamp,
            "processed_by": self.processed_by,
        }


# Pre-defined event chains — when event X fires, trigger handler Y
EVENT_CHAINS = {
    EventCategory.DATA_LEAK: [
        ("soar", "trigger_playbook", {"playbook": "data_exfiltration"}),
        ("containment", "escalate", {"level": "block"}),
        ("forensics", "collect_evidence", {"type": "data_leak"}),
        ("governance", "update_risk", {"category": "data_breach"}),
    ],
    EventCategory.THREAT_DETECTED: [
        ("soar", "trigger_playbook", {"playbook": "intrusion_detected"}),
        ("ctip", "enrich", {}),
        ("containment", "evaluate", {}),
        ("forensics", "timeline_event", {}),
    ],
    EventCategory.AUTH_FAILURE: [
        ("soar", "trigger_playbook", {"playbook": "credential_stuffing"}),
        ("containment", "throttle", {}),
    ],
    EventCategory.POLICY_VIOLATION: [
        ("audit", "log_violation", {}),
        ("governance", "update_controls", {}),
    ],
    EventCategory.INCIDENT: [
        ("soar", "trigger_playbook", {"playbook": "generic_incident"}),
        ("forensics", "collect_evidence", {"type": "incident"}),
        ("containment", "evaluate", {}),
        ("governance", "update_risk", {}),
    ],
}


class EventSubscription:
    """A subscriber to specific event categories."""

    def __init__(self, sub_id: str, name: str,
                 categories: List[EventCategory],
                 handler: Optional[Callable] = None):
        self.sub_id = sub_id
        self.name = name
        self.categories = categories
        self.handler = handler
        self.received = 0

    def to_dict(self) -> Dict:
        return {"id": self.sub_id, "name": self.name,
                "categories": [c.value for c in self.categories],
                "received": self.received}


class SecurityEventBus:
    """Internal event bus for cross-module security event propagation."""

    def __init__(self):
        self._events: List[SecurityEvent] = []
        self._subscriptions: Dict[str, EventSubscription] = {}
        self._event_counter = 0
        self._sub_counter = 0
        self._lock = threading.Lock()
        self._chains = EVENT_CHAINS

    def emit(self, category: EventCategory, severity: EventSeverity,
             source: str, description: str,
             data: Optional[Dict] = None) -> SecurityEvent:
        """Emit a security event to the bus."""
        with self._lock:
            self._event_counter += 1
            event_id = f"EVT-{self._event_counter:010d}"

        event = SecurityEvent(event_id, category, severity,
                             source, description, data)
        self._events.append(event)

        # Notify subscribers
        for sub in self._subscriptions.values():
            if category in sub.categories:
                sub.received += 1
                event.processed_by.append(sub.name)
                if sub.handler:
                    try:
                        sub.handler(event)
                    except Exception as e:
                        logger.error(f"Handler {sub.name} failed: {e}")

        event.propagated = True
        logger.info(f"Event {event_id}: [{severity.value}] {source} → {description[:60]}")
        return event

    def subscribe(self, name: str, categories: List[EventCategory],
                  handler: Optional[Callable] = None) -> EventSubscription:
        """Subscribe to specific event categories."""
        with self._lock:
            self._sub_counter += 1
            sub_id = f"SUB-{self._sub_counter:06d}"
        sub = EventSubscription(sub_id, name, categories, handler)
        self._subscriptions[sub_id] = sub
        return sub

    def unsubscribe(self, sub_id: str) -> bool:
        return self._subscriptions.pop(sub_id, None) is not None

    def get_events(self, category: Optional[EventCategory] = None,
                   severity: Optional[EventSeverity] = None,
                   limit: int = 50) -> List[Dict]:
        """Query recent events with optional filtering."""
        events = self._events
        if category:
            events = [e for e in events if e.category == category]
        if severity:
            events = [e for e in events if e.severity == severity]
        return [e.to_dict() for e in events[-limit:]]

    def get_chain(self, category: EventCategory) -> List[Dict]:
        """Get the pre-defined chain for an event category."""
        chain = self._chains.get(category, [])
        return [{"module": mod, "action": act, "params": params}
                for mod, act, params in chain]

    def get_stats(self) -> Dict:
        return {
            "total_events": len(self._events),
            "subscriptions": len(self._subscriptions),
            "event_chains": len(self._chains),
            "by_severity": {s.value: sum(1 for e in self._events
                                          if e.severity == s)
                            for s in EventSeverity},
            "by_category": {c.value: sum(1 for e in self._events
                                          if e.category == c)
                            for c in EventCategory},
        }


event_bus = SecurityEventBus()
