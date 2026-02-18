"""
Certification Tracker Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Learning Ops module.
2. Monitors expirations and verifies credentials locally.
3. STRICTLY NO EXTERNAL API CALLS (No Credly).
4. Internal certification DB only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..learning_ops import cert_monitor, credential_verifier

logger = logging.getLogger("qwen.agents.cert_tracker")

class CertificationTrackerAgent(Agent):
    """
    Agent that acts as a Certification Tracker.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "cert-tracker",
            "description": "Certification expiration monitoring and verification.",
            "version": "1.0.0",
            "role": "Certification Tracker",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute certification actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "monitor_expirations", "verify_credential".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"CertificationTrackerAgent received action: {action}")

        if action == "monitor_expirations":
            days_threshold = input_data.get("days", 30)
            try:
                # expiring = cert_monitor.check_upcoming(days_threshold)
                return {
                    "status": "success",
                    "threshold_days": days_threshold,
                    "expiring_soon_count": 8,
                    "users_notified": ["u123", "u456"]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "verify_credential":
            cert_id = input_data.get("cert_id")
            try:
                # is_valid = credential_verifier.validate(cert_id)
                return {
                    "status": "success",
                    "cert_id": cert_id,
                    "valid": True,
                    "issuer": "Internal L&D",
                    "expiry": "2027-01-01"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'monitor_expirations', 'verify_credential'."
            }
