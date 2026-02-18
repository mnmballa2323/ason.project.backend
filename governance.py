"""
Governance & Policy Engine — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Automated policy enforcement for S&P 500 regulatory compliance.
"""
import json, logging, time, threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("qwen.governance")

class PolicySeverity(str, Enum):
    MANDATORY = "mandatory"
    RECOMMENDED = "recommended"
    ADVISORY = "advisory"

class PolicyScope(str, Enum):
    GLOBAL = "global"
    TENANT = "tenant"
    ROLE = "role"
    DATA_CLASSIFICATION = "data_classification"

class PolicyVerdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"

class Policy:
    """A governance policy rule."""
    def __init__(self, policy_id, name, description, severity,
                 scope, condition_fn, action=PolicyVerdict.DENY):
        self.policy_id = policy_id
        self.name = name
        self.description = description
        self.severity = severity
        self.scope = scope
        self.condition_fn = condition_fn
        self.action = action
        self.enabled = True
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.violations_count = 0
        self.last_violation = None

    def evaluate(self, context: Dict) -> Dict:
        try:
            violated = self.condition_fn(context)
        except Exception as e:
            return {"policy": self.policy_id, "verdict": "error", "error": str(e)}
        if violated:
            self.violations_count += 1
            self.last_violation = datetime.now(timezone.utc).isoformat()
            return {
                "policy": self.policy_id, "name": self.name,
                "verdict": self.action.value, "severity": self.severity.value,
                "description": self.description,
            }
        return {"policy": self.policy_id, "verdict": PolicyVerdict.ALLOW.value}

    def to_dict(self):
        return {
            "policy_id": self.policy_id, "name": self.name,
            "severity": self.severity.value, "scope": self.scope.value,
            "action": self.action.value, "enabled": self.enabled,
            "violations": self.violations_count, "last_violation": self.last_violation,
        }

class GovernanceEngine:
    """Automated policy enforcement engine."""
    def __init__(self):
        self._policies: Dict[str, Policy] = {}
        self._violation_log: List[Dict] = []
        self._lock = threading.Lock()
        self._register_defaults()

    def _register_defaults(self):
        self.register(Policy("GOV-001", "MFA Required for Admin",
            "All admin operations require MFA", PolicySeverity.MANDATORY,
            PolicyScope.ROLE, lambda ctx: ctx.get("role") == "admin" and not ctx.get("mfa_verified")))
        self.register(Policy("GOV-002", "Restricted Data Encryption",
            "RESTRICTED data must be encrypted at rest", PolicySeverity.MANDATORY,
            PolicyScope.DATA_CLASSIFICATION,
            lambda ctx: ctx.get("classification") == "RESTRICTED" and not ctx.get("encrypted")))
        self.register(Policy("GOV-003", "Change Approval Required",
            "Production changes require CAB approval", PolicySeverity.MANDATORY,
            PolicyScope.GLOBAL,
            lambda ctx: ctx.get("environment") == "production" and not ctx.get("cab_approved")))
        self.register(Policy("GOV-004", "Data Retention Compliance",
            "Financial data must be retained for 7 years", PolicySeverity.MANDATORY,
            PolicyScope.DATA_CLASSIFICATION,
            lambda ctx: ctx.get("category") == "financial" and ctx.get("retention_days", 9999) < 2555))
        self.register(Policy("GOV-005", "API Key Rotation",
            "API keys must be rotated every 90 days", PolicySeverity.RECOMMENDED,
            PolicyScope.GLOBAL,
            lambda ctx: ctx.get("key_age_days", 0) > 90 and ctx.get("resource_type") == "api_key"))
        self.register(Policy("GOV-006", "Segregation of Duties",
            "Approver cannot be the same as requester", PolicySeverity.MANDATORY,
            PolicyScope.GLOBAL,
            lambda ctx: ctx.get("requester") == ctx.get("approver") and ctx.get("requester")))
        self.register(Policy("GOV-007", "Minimum Password Complexity",
            "Passwords must meet NIST SP 800-63B requirements", PolicySeverity.MANDATORY,
            PolicyScope.GLOBAL,
            lambda ctx: ctx.get("resource_type") == "password" and len(ctx.get("value", "")) < 12))
        self.register(Policy("GOV-008", "Audit Log Immutability",
            "Audit logs must not be deletable", PolicySeverity.MANDATORY,
            PolicyScope.GLOBAL,
            lambda ctx: ctx.get("action") == "delete" and ctx.get("resource_type") == "audit_log"))

    def register(self, policy: Policy):
        self._policies[policy.policy_id] = policy

    def evaluate(self, context: Dict) -> Dict:
        results = []
        denied = False
        warnings = []
        for policy in self._policies.values():
            if not policy.enabled:
                continue
            result = policy.evaluate(context)
            results.append(result)
            if result["verdict"] == PolicyVerdict.DENY.value:
                denied = True
                with self._lock:
                    self._violation_log.append({**result,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "context_summary": {k: str(v)[:100] for k, v in context.items()},
                    })
            elif result["verdict"] == PolicyVerdict.WARN.value:
                warnings.append(result)
        return {
            "allowed": not denied,
            "violations": [r for r in results if r["verdict"] == PolicyVerdict.DENY.value],
            "warnings": warnings,
            "policies_evaluated": len(results),
        }

    def get_violations(self, limit=100):
        return self._violation_log[-limit:]

    def get_compliance_posture(self):
        total = len(self._policies)
        mandatory = sum(1 for p in self._policies.values() if p.severity == PolicySeverity.MANDATORY)
        violated = sum(1 for p in self._policies.values() if p.violations_count > 0)
        return {
            "total_policies": total, "mandatory": mandatory,
            "with_violations": violated,
            "compliance_score": round((total - violated) / max(1, total) * 100, 1),
            "policies": [p.to_dict() for p in self._policies.values()],
        }

governance_engine = GovernanceEngine()
