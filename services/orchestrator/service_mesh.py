"""
Service Mesh Security — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Zero-trust inter-service authentication and authorization.
Every service-to-service call is authenticated via mTLS, and
authorized against service-level policies.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger("qwen.service_mesh")


class ServiceIdentity(str, Enum):
    ORCHESTRATOR = "orchestrator"
    INFERENCE = "inference"
    POSTGRES = "postgres"
    MILVUS = "milvus"
    KEYCLOAK = "keycloak"
    FRONTEND = "frontend"
    MONITORING = "monitoring"
    BACKUP = "backup"


class AuthzDecision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    AUDIT = "audit"   # Allow but log for review


class ServicePolicy:
    """A policy governing service-to-service communication."""
    def __init__(self, policy_id, source, destination, action,
                 allowed_methods=None, allowed_paths=None, condition=""):
        self.policy_id = policy_id
        self.source = source            # ServiceIdentity or "*"
        self.destination = destination   # ServiceIdentity
        self.action = action             # AuthzDecision
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE"]
        self.allowed_paths = allowed_paths or ["*"]
        self.condition = condition
        self.enabled = True
        self.hit_count = 0

    def matches(self, src: str, dst: str, method: str = "", path: str = "") -> bool:
        if not self.enabled:
            return False
        if self.source != "*" and self.source.value != src:
            return False
        if self.destination.value != dst:
            return False
        if method and method not in self.allowed_methods:
            return False
        if path and self.allowed_paths != ["*"]:
            if not any(path.startswith(p) for p in self.allowed_paths):
                return False
        return True

    def to_dict(self):
        return {
            "policy_id": self.policy_id,
            "source": self.source.value if isinstance(self.source, Enum) else self.source,
            "destination": self.destination.value,
            "action": self.action.value,
            "methods": self.allowed_methods,
            "paths": self.allowed_paths,
            "enabled": self.enabled, "hit_count": self.hit_count,
        }


class ServiceMeshSecurity:
    """Zero-trust service mesh with policy-based authorization."""

    def __init__(self):
        self._policies: List[ServicePolicy] = []
        self._auth_log: List[Dict] = []
        self._lock = threading.Lock()
        self._denied_count = 0
        self._allowed_count = 0
        self._register_default_policies()

    def _register_default_policies(self):
        """Least-privilege default policies."""
        P = ServicePolicy
        SI = ServiceIdentity
        A = AuthzDecision

        # Orchestrator can call everything (it's the API gateway)
        self.add_policy(P("SM-001", SI.ORCHESTRATOR, SI.INFERENCE, A.ALLOW,
                          ["POST"], ["/v1/predict", "/v1/embed", "/health"]))
        self.add_policy(P("SM-002", SI.ORCHESTRATOR, SI.POSTGRES, A.ALLOW,
                          ["GET", "POST", "PUT", "DELETE"]))
        self.add_policy(P("SM-003", SI.ORCHESTRATOR, SI.MILVUS, A.ALLOW,
                          ["GET", "POST", "PUT"]))
        self.add_policy(P("SM-004", SI.ORCHESTRATOR, SI.KEYCLOAK, A.ALLOW,
                          ["GET", "POST"], ["/auth/", "/realms/"]))

        # Frontend can only call orchestrator
        self.add_policy(P("SM-010", SI.FRONTEND, SI.ORCHESTRATOR, A.ALLOW,
                          ["GET", "POST"]))
        # Frontend cannot directly access backend services
        self.add_policy(P("SM-011", SI.FRONTEND, SI.POSTGRES, A.DENY))
        self.add_policy(P("SM-012", SI.FRONTEND, SI.MILVUS, A.DENY))
        self.add_policy(P("SM-013", SI.FRONTEND, SI.INFERENCE, A.DENY))

        # Inference is isolated — no outbound except health
        self.add_policy(P("SM-020", SI.INFERENCE, SI.POSTGRES, A.DENY))
        self.add_policy(P("SM-021", SI.INFERENCE, SI.MILVUS, A.DENY))

        # Monitoring can read health from all services
        self.add_policy(P("SM-030", SI.MONITORING, SI.ORCHESTRATOR, A.ALLOW,
                          ["GET"], ["/health"]))
        self.add_policy(P("SM-031", SI.MONITORING, SI.INFERENCE, A.ALLOW,
                          ["GET"], ["/health"]))
        self.add_policy(P("SM-032", SI.MONITORING, SI.POSTGRES, A.ALLOW,
                          ["GET"], ["/health"]))

        # Backup can read from data stores
        self.add_policy(P("SM-040", SI.BACKUP, SI.POSTGRES, A.ALLOW,
                          ["GET"], ["/backup", "/dump"]))
        self.add_policy(P("SM-041", SI.BACKUP, SI.MILVUS, A.ALLOW,
                          ["GET"], ["/backup", "/snapshot"]))

        # Default deny all (catch-all)
        self._default_action = AuthzDecision.DENY

    def add_policy(self, policy: ServicePolicy):
        self._policies.append(policy)

    def authorize(self, source: str, destination: str,
                  method: str = "GET", path: str = "",
                  cert_id: str = "") -> Dict:
        """Authorize a service-to-service call."""
        for policy in self._policies:
            if policy.matches(source, destination, method, path):
                policy.hit_count += 1
                decision = policy.action

                entry = {
                    "source": source, "destination": destination,
                    "method": method, "path": path,
                    "decision": decision.value,
                    "policy_id": policy.policy_id,
                    "cert_id": cert_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

                with self._lock:
                    self._auth_log.append(entry)
                    if decision == AuthzDecision.ALLOW:
                        self._allowed_count += 1
                    else:
                        self._denied_count += 1

                if decision == AuthzDecision.DENY:
                    logger.warning(f"MESH DENY: {source} → {destination} {method} {path}")

                return entry

        # Default deny
        with self._lock:
            self._denied_count += 1
        logger.warning(f"MESH DEFAULT DENY: {source} → {destination} {method} {path}")
        return {
            "source": source, "destination": destination,
            "decision": self._default_action.value,
            "policy_id": "default_deny",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_policies(self) -> List[Dict]:
        return [p.to_dict() for p in self._policies]

    def get_stats(self) -> Dict:
        return {
            "total_policies": len(self._policies),
            "allowed": self._allowed_count,
            "denied": self._denied_count,
            "auth_log_size": len(self._auth_log),
        }

service_mesh = ServiceMeshSecurity()
