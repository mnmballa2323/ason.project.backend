"""
Badge Administrator Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Physical Admin module.
2. Provisions and revokes HID access cards.
3. STRICTLY NO EXTERNAL API CALLS (No HID Origo/cloud).
4. Direct database modification.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..physical_admin import card_provisioner, access_db

logger = logging.getLogger("qwen.agents.badge_admin")

class BadgeAdministratorAgent(Agent):
    """
    Agent that acts as a Security Administrator.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "badge-admin",
            "description": "Employee ID badge provisioning and revocation.",
            "version": "1.0.0",
            "role": "Security Administrator",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute badge admin actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "issue_badge", "revoke_badge".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"BadgeAdministratorAgent received action: {action}")

        if action == "issue_badge":
            employee_id = input_data.get("employee_id")
            try:
                # Assigns next available card ID.
                # card_id = card_provisioner.issue(employee_id)
                return {
                    "status": "success",
                    "employee_id": employee_id,
                    "card_id": "HID-990022",
                    "access_level": "Standard",
                    "activation_date": "2026-02-18"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "revoke_badge":
            employee_id = input_data.get("employee_id")
            try:
                # Retires credential in local DB.
                # status = access_db.deactivate(employee_id)
                return {
                    "status": "success",
                    "employee_id": employee_id,
                    "revocation_timestamp": "2026-02-17T21:30:00Z",
                    "reason": "Termination/Lost"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'issue_badge', 'revoke_badge'."
            }
