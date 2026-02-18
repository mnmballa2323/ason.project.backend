"""
Network Segmentation Controller — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Microsegmentation rules for defense-in-depth networking.
Defines security zones, allowed traffic flows, and
network access control lists (NACLs) for zero-trust.
"""

import logging
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.network_segmentation")


class SecurityZone(str, Enum):
    DMZ = "dmz"                     # Public-facing (load balancer, WAF)
    APPLICATION = "application"      # Orchestrator, frontend
    DATA = "data"                    # Postgres, Milvus
    INFERENCE = "inference"          # AI/ML inference engines
    IDENTITY = "identity"           # Keycloak, auth services
    MANAGEMENT = "management"       # Monitoring, backup, admin
    RESTRICTED = "restricted"       # Key management, HSM, audit


class Protocol(str, Enum):
    TCP = "tcp"
    UDP = "udp"
    HTTPS = "https"
    GRPC = "grpc"


class FlowAction(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    LOG = "log_and_allow"


class NetworkRule:
    """A microsegmentation rule defining allowed traffic flow."""
    def __init__(self, rule_id, source_zone, dest_zone, action,
                 protocol=Protocol.HTTPS, port=443, description=""):
        self.rule_id = rule_id
        self.source_zone = source_zone
        self.dest_zone = dest_zone
        self.action = action
        self.protocol = protocol
        self.port = port
        self.description = description
        self.enabled = True
        self.hit_count = 0
        self.created_at = datetime.now(timezone.utc).isoformat()

    def matches(self, src_zone: str, dst_zone: str, port: int = 0) -> bool:
        if not self.enabled:
            return False
        if self.source_zone.value != src_zone:
            return False
        if self.dest_zone.value != dst_zone:
            return False
        if port and self.port != port:
            return False
        return True

    def to_dict(self):
        return {
            "rule_id": self.rule_id,
            "source": self.source_zone.value,
            "destination": self.dest_zone.value,
            "action": self.action.value,
            "protocol": self.protocol.value,
            "port": self.port,
            "description": self.description,
            "hit_count": self.hit_count,
        }


class NetworkSegmentationController:
    """Microsegmentation controller for zero-trust networking."""

    def __init__(self):
        self._rules: List[NetworkRule] = []
        self._violations: List[Dict] = []
        self._lock = threading.Lock()
        self._register_default_rules()

    def _register_default_rules(self):
        R = NetworkRule
        Z = SecurityZone
        A = FlowAction
        P = Protocol

        # DMZ → Application only (HTTPS)
        self.add(R("NET-001", Z.DMZ, Z.APPLICATION, A.ALLOW,
                    P.HTTPS, 443, "External traffic to application layer"))
        self.add(R("NET-002", Z.DMZ, Z.DATA, A.DENY,
                    description="No direct DMZ access to data layer"))
        self.add(R("NET-003", Z.DMZ, Z.INFERENCE, A.DENY,
                    description="No direct DMZ access to inference"))
        self.add(R("NET-004", Z.DMZ, Z.RESTRICTED, A.DENY,
                    description="No DMZ access to restricted zone"))

        # Application → Data (Postgres 5432, Milvus 19530)
        self.add(R("NET-010", Z.APPLICATION, Z.DATA, A.ALLOW,
                    P.TCP, 5432, "Orchestrator → Postgres"))
        self.add(R("NET-011", Z.APPLICATION, Z.DATA, A.ALLOW,
                    P.GRPC, 19530, "Orchestrator → Milvus"))
        self.add(R("NET-012", Z.APPLICATION, Z.INFERENCE, A.ALLOW,
                    P.HTTPS, 8080, "Orchestrator → Inference API"))
        self.add(R("NET-013", Z.APPLICATION, Z.IDENTITY, A.ALLOW,
                    P.HTTPS, 8443, "Orchestrator → Keycloak"))

        # Identity zone is isolated
        self.add(R("NET-020", Z.IDENTITY, Z.DATA, A.ALLOW,
                    P.TCP, 5432, "Keycloak → Postgres (user store)"))
        self.add(R("NET-021", Z.IDENTITY, Z.INFERENCE, A.DENY,
                    description="Identity cannot access inference"))

        # Inference zone is maximally isolated
        self.add(R("NET-030", Z.INFERENCE, Z.DATA, A.DENY,
                    description="Inference cannot access data stores directly"))
        self.add(R("NET-031", Z.INFERENCE, Z.IDENTITY, A.DENY,
                    description="Inference cannot access identity"))
        self.add(R("NET-032", Z.INFERENCE, Z.RESTRICTED, A.DENY,
                    description="Inference cannot access restricted zone"))

        # Management zone (monitoring, backup)
        self.add(R("NET-040", Z.MANAGEMENT, Z.APPLICATION, A.LOG,
                    P.HTTPS, 443, "Monitoring → Application (health checks)"))
        self.add(R("NET-041", Z.MANAGEMENT, Z.DATA, A.LOG,
                    P.TCP, 5432, "Backup → Postgres (read-only)"))
        self.add(R("NET-042", Z.MANAGEMENT, Z.INFERENCE, A.LOG,
                    P.HTTPS, 8080, "Monitoring → Inference (health)"))

        # Restricted zone — audit, keys, HSM
        self.add(R("NET-050", Z.APPLICATION, Z.RESTRICTED, A.LOG,
                    P.HTTPS, 8443, "Orchestrator → Key Management (logged)"))
        self.add(R("NET-051", Z.RESTRICTED, Z.DATA, A.ALLOW,
                    P.TCP, 5432, "Audit → Postgres (write audit logs)"))
        self.add(R("NET-052", Z.DATA, Z.RESTRICTED, A.DENY,
                    description="Data zone cannot reach restricted"))

    def add(self, rule: NetworkRule):
        self._rules.append(rule)

    def evaluate(self, source_zone: str, dest_zone: str, port: int = 0) -> Dict:
        """Evaluate traffic flow against microsegmentation rules."""
        for rule in self._rules:
            if rule.matches(source_zone, dest_zone, port):
                rule.hit_count += 1
                result = {
                    "action": rule.action.value,
                    "rule_id": rule.rule_id,
                    "source": source_zone, "dest": dest_zone,
                    "port": port,
                }
                if rule.action == FlowAction.DENY:
                    with self._lock:
                        self._violations.append({
                            **result,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                    logger.warning(f"SEGMENTATION DENY: {source_zone} → {dest_zone}:{port}")
                return result

        # Default deny
        with self._lock:
            self._violations.append({
                "action": "deny", "rule_id": "default_deny",
                "source": source_zone, "dest": dest_zone,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        return {"action": "deny", "rule_id": "default_deny"}

    def get_flow_matrix(self) -> Dict:
        """Generate a zone-to-zone traffic flow matrix."""
        zones = [z.value for z in SecurityZone]
        matrix = {}
        for src in zones:
            matrix[src] = {}
            for dst in zones:
                if src == dst:
                    matrix[src][dst] = "self"
                    continue
                result = None
                for rule in self._rules:
                    if rule.matches(src, dst):
                        result = rule.action.value
                        break
                matrix[src][dst] = result or "deny"
        return matrix

    def get_violations(self, limit=100) -> List[Dict]:
        return self._violations[-limit:]

    def get_stats(self) -> Dict:
        return {
            "total_rules": len(self._rules),
            "zones": [z.value for z in SecurityZone],
            "violations": len(self._violations),
            "rules": [r.to_dict() for r in self._rules],
        }

segmentation_controller = NetworkSegmentationController()
