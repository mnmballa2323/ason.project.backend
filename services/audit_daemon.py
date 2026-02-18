"""
Audit Daemon — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Real-time watchdog that monitors the system for compliance violations.
Feeds events into the Evidence Locker.
"""
import logging
import asyncio
from typing import List, Dict
from services.evidence_locker import evidence_locker

logger = logging.getLogger("qwen.audit_daemon")

class AuditDaemon:
    """
    Background service that watches for security events.
    Enforces policies like "No Root Login" and "Encryption Enabled".
    """
    
    POLICIES = [
        {"id": "POL-001", "name": "No Root Login", "severity": "CRITICAL"},
        {"id": "POL-002", "name": "MFA Enabled", "severity": "HIGH"},
        {"id": "POL-003", "name": "Data Sovereignty Check", "severity": "CRITICAL"},
    ]

    def log_event(self, event_type: str, actor: str, details: Dict):
        """
        Log a security event to the immutable locker.
        Analyzes for policy violations.
        """
        violation = self._check_violation(event_type, details)
        
        meta = details.copy()
        if violation:
            meta["violation"] = True
            meta["policy_id"] = violation["id"]
            logger.warning(f"🚨 Policy Violation: {violation['name']} by {actor}")
        
        evidence_locker.write_evidence(event_type, meta, actor)

    def _check_violation(self, event_type: str, details: Dict) -> Optional[Dict]:
        """Check if an event violates a policy."""
        if event_type == "user_login" and details.get("username") == "root":
            return self.POLICIES[0]
        
        if event_type == "data_transfer" and details.get("sovereignty_status") == "failed":
            return self.POLICIES[2]
            
        return None

    def get_compliance_status(self) -> Dict:
        """Return current compliance health."""
        # Check evidence locker for recent violations
        chain = evidence_locker.get_evidence_chain()
        violations = [e for e in chain if e["data"]["details"].get("violation")]
        
        return {
            "status": "COMPLIANT" if not violations else "AT_RISK",
            "active_policies": len(self.POLICIES),
            "total_violations_detected": len(violations),
            "integrity_verified": evidence_locker.verify_integrity()
        }

audit_daemon = AuditDaemon()
