"""
Security Mesh Architecture — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Decentralized enforcement, policy federation, zero trust fabric.
"""

import hashlib, hmac, logging, os, threading, time
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.security_mesh")


# ============================================================================
#  SECURITY MESH
# ============================================================================

class MeshNodeRole(str, Enum):
    ENFORCER = "enforcer"
    OBSERVER = "observer"
    COORDINATOR = "coordinator"
    GATEWAY = "gateway"


class MeshPolicy:
    def __init__(self, policy_id, name, rules, priority, enforcement):
        self.policy_id = policy_id
        self.name = name
        self.rules = rules  # List of condition dicts
        self.priority = priority
        self.enforcement = enforcement  # "enforce" or "audit"
        self.version = 1
        self.applied_count = 0

    def to_dict(self):
        return {"id": self.policy_id, "name": self.name,
                "rules": len(self.rules), "priority": self.priority,
                "enforcement": self.enforcement, "version": self.version}


class MeshNode:
    def __init__(self, node_id, service_name, role, region):
        self.node_id = node_id
        self.service_name = service_name
        self.role = role
        self.region = region
        self.policies: List[str] = []
        self.status = "active"
        self.last_sync = datetime.now(timezone.utc)
        self.decisions = 0
        self.cert_fingerprint = hashlib.sha256(os.urandom(32)).hexdigest()[:16]

    def to_dict(self):
        return {"id": self.node_id, "service": self.service_name,
                "role": self.role.value, "region": self.region,
                "policies": len(self.policies), "decisions": self.decisions,
                "cert": self.cert_fingerprint}


class SecurityMesh:
    """Decentralized security — each service enforces its own policies."""

    def __init__(self):
        self._nodes: Dict[str, MeshNode] = {}
        self._policies: Dict[str, MeshPolicy] = {}
        self._sync_log: List[Dict] = []
        self._seed()

    def _seed(self):
        nodes = [
            ("mesh-gw-01", "api-gateway", MeshNodeRole.GATEWAY, "us-east-1"),
            ("mesh-auth-01", "auth-service", MeshNodeRole.ENFORCER, "us-east-1"),
            ("mesh-verify-01", "verification-engine", MeshNodeRole.ENFORCER, "us-east-1"),
            ("mesh-hub-01", "security-hub", MeshNodeRole.COORDINATOR, "us-east-1"),
            ("mesh-lake-01", "data-lake", MeshNodeRole.OBSERVER, "us-east-1"),
            ("mesh-gw-02", "api-gateway-dr", MeshNodeRole.GATEWAY, "us-west-2"),
            ("mesh-auth-02", "auth-service-dr", MeshNodeRole.ENFORCER, "us-west-2"),
            ("mesh-hub-02", "security-hub-dr", MeshNodeRole.COORDINATOR, "eu-west-1"),
        ]
        for nid, svc, role, region in nodes:
            self._nodes[nid] = MeshNode(nid, svc, role, region)

        policies = [
            ("MP-001", "Mutual TLS Required",
             [{"field": "tls_version", "operator": "gte", "value": "1.3"},
              {"field": "mutual_auth", "operator": "eq", "value": True}], 1, "enforce"),
            ("MP-002", "Rate Limit Enforcement",
             [{"field": "requests_per_min", "operator": "lte", "value": 100}], 2, "enforce"),
            ("MP-003", "JWT Token Validation",
             [{"field": "jwt_valid", "operator": "eq", "value": True},
              {"field": "jwt_not_expired", "operator": "eq", "value": True}], 1, "enforce"),
            ("MP-004", "Request Size Limit",
             [{"field": "body_bytes", "operator": "lte", "value": 1048576}], 3, "enforce"),
            ("MP-005", "Geo-Blocking Sanctioned Countries",
             [{"field": "geo_country", "operator": "not_in",
               "value": ["KP", "IR", "SY", "CU"]}], 1, "enforce"),
            ("MP-006", "Audit All Admin Actions",
             [{"field": "role", "operator": "eq", "value": "admin"}], 5, "audit"),
        ]
        for pid, name, rules, prio, enforcement in policies:
            policy = MeshPolicy(pid, name, rules, prio, enforcement)
            self._policies[pid] = policy
            for node in self._nodes.values():
                node.policies.append(pid)

    def enforce(self, node_id: str, request: Dict) -> Dict:
        node = self._nodes.get(node_id)
        if not node:
            return {"allowed": False, "reason": "Unknown node"}
        node.decisions += 1
        violations = []
        for pid in node.policies:
            policy = self._policies.get(pid)
            if not policy:
                continue
            for rule in policy.rules:
                field = rule["field"]
                operator = rule["operator"]
                expected = rule["value"]
                actual = request.get(field)
                if operator == "eq" and actual != expected:
                    violations.append({"policy": pid, "field": field, "expected": expected, "actual": actual})
                elif operator == "gte" and (actual is None or actual < expected):
                    violations.append({"policy": pid, "field": field})
                elif operator == "lte" and (actual is not None and actual > expected):
                    violations.append({"policy": pid, "field": field})
                elif operator == "not_in" and actual in (expected if isinstance(expected, list) else [expected]):
                    violations.append({"policy": pid, "field": field, "blocked_value": actual})
            policy.applied_count += 1
        allowed = len(violations) == 0
        return {"allowed": allowed, "violations": violations,
                "node": node_id, "policies_evaluated": len(node.policies)}

    def sync_policies(self) -> Dict:
        synced = 0
        for node in self._nodes.values():
            node.last_sync = datetime.now(timezone.utc)
            synced += 1
        record = {"synced": synced, "ts": datetime.now(timezone.utc).isoformat()}
        self._sync_log.append(record)
        return record

    def get_stats(self) -> Dict:
        return {"nodes": len(self._nodes), "policies": len(self._policies),
                "total_decisions": sum(n.decisions for n in self._nodes.values())}


# ============================================================================
#  POLICY FEDERATION
# ============================================================================

class FederatedOrg:
    def __init__(self, org_id, name, trust_level, policies):
        self.org_id = org_id
        self.name = name
        self.trust_level = trust_level  # 1-10
        self.policies = policies
        self.synced = False

    def to_dict(self):
        return {"id": self.org_id, "name": self.name,
                "trust": self.trust_level, "policies": len(self.policies)}


class PolicyFederation:
    """Federate policies across multi-cloud, multi-region, multi-org."""

    def __init__(self):
        self._orgs: Dict[str, FederatedOrg] = {}
        self._cross_policies: List[Dict] = []
        self._seed()

    def _seed(self):
        orgs = [
            ("org-primary", "Primary (Production)", 10, [
                "enforce_mfa", "encrypt_all", "audit_log", "zero_trust",
                "dlp_enforced", "patch_sla_7d"]),
            ("org-staging", "Staging Environment", 7, [
                "enforce_mfa", "encrypt_all", "audit_log"]),
            ("org-dev", "Development", 5, [
                "audit_log", "basic_auth"]),
            ("org-partner-a", "Partner A (Financial)", 8, [
                "encrypt_all", "audit_log", "data_residency_us",
                "sox_compliance"]),
            ("org-partner-b", "Partner B (Healthcare)", 8, [
                "encrypt_all", "audit_log", "data_residency_us",
                "hipaa_compliance", "baa_required"]),
            ("org-govcloud", "GovCloud", 10, [
                "fedramp_high", "fips_140_3", "encrypt_all", "zero_trust",
                "cjis_compliance", "itar_restricted"]),
        ]
        for oid, name, trust, policies in orgs:
            self._orgs[oid] = FederatedOrg(oid, name, trust, policies)

    def federate_policy(self, source_org: str, target_org: str,
                       policy_name: str) -> Dict:
        source = self._orgs.get(source_org)
        target = self._orgs.get(target_org)
        if not source or not target:
            return {"error": "Organization not found"}
        if target.trust_level < 5:
            return {"error": "Target org trust level too low"}
        if policy_name not in source.policies:
            return {"error": "Policy not found in source org"}
        if policy_name not in target.policies:
            target.policies.append(policy_name)
        record = {"source": source_org, "target": target_org,
                  "policy": policy_name,
                  "ts": datetime.now(timezone.utc).isoformat()}
        self._cross_policies.append(record)
        return record

    def sync_all(self) -> Dict:
        for org in self._orgs.values():
            org.synced = True
        return {"synced": len(self._orgs)}

    def get_compliance_matrix(self) -> Dict:
        matrix = {}
        for org in self._orgs.values():
            matrix[org.name] = {
                "policies": org.policies,
                "count": len(org.policies),
                "trust": org.trust_level,
            }
        return matrix

    def get_stats(self) -> Dict:
        return {"organizations": len(self._orgs),
                "cross_policies": len(self._cross_policies)}


# ============================================================================
#  ZERO TRUST FABRIC
# ============================================================================

class ZeroTrustVerdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"
    STEP_UP = "step_up_auth"


class TrustSignal:
    def __init__(self, name, weight, value):
        self.name = name
        self.weight = weight  # 0.0-1.0
        self.value = value    # 0.0-1.0 (1.0 = fully trusted)

    def score(self):
        return self.weight * self.value


class ZeroTrustFabric:
    """Every request authenticated + authorized + encrypted at every hop."""

    TRUST_SIGNALS = [
        ("identity_verified", 0.20),
        ("mfa_completed", 0.15),
        ("device_compliant", 0.15),
        ("network_trusted", 0.10),
        ("geo_expected", 0.10),
        ("time_normal", 0.05),
        ("behavior_normal", 0.10),
        ("cert_valid", 0.10),
        ("encryption_strong", 0.05),
    ]

    def __init__(self):
        self._evaluations = 0
        self._denials = 0
        self._challenges = 0

    def evaluate_trust(self, request: Dict) -> Dict:
        self._evaluations += 1
        signals = []
        total_score = 0

        for signal_name, weight in self.TRUST_SIGNALS:
            value = request.get(signal_name, 0.5)  # Default: uncertain
            signal = TrustSignal(signal_name, weight, value)
            score = signal.score()
            total_score += score
            signals.append({"signal": signal_name, "weight": weight,
                          "value": value, "score": round(score, 4)})

        # Determine verdict
        if total_score >= 0.80:
            verdict = ZeroTrustVerdict.ALLOW
        elif total_score >= 0.60:
            verdict = ZeroTrustVerdict.STEP_UP
            self._challenges += 1
        elif total_score >= 0.40:
            verdict = ZeroTrustVerdict.CHALLENGE
            self._challenges += 1
        else:
            verdict = ZeroTrustVerdict.DENY
            self._denials += 1

        # Micro-segmentation check
        source = request.get("source_service", "unknown")
        target = request.get("target_service", "unknown")
        allowed_paths = request.get("allowed_service_paths", [])
        path_allowed = not allowed_paths or f"{source}→{target}" in allowed_paths

        return {
            "trust_score": round(total_score, 4),
            "verdict": verdict.value,
            "signals": signals,
            "path_allowed": path_allowed,
            "encrypted": request.get("encryption_strong", 0) > 0.5,
            "ts": datetime.now(timezone.utc).isoformat(),
        }

    def get_stats(self) -> Dict:
        return {"evaluations": self._evaluations,
                "denials": self._denials, "challenges": self._challenges,
                "allow_rate": round(
                    (self._evaluations - self._denials - self._challenges) /
                    max(self._evaluations, 1) * 100, 1)}


# Singletons
security_mesh = SecurityMesh()
policy_federation = PolicyFederation()
zero_trust_fabric = ZeroTrustFabric()
