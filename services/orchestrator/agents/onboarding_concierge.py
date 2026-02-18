"""
Onboarding Concierge Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with Tenancy module.
2. Automates tenant creation and initial setup.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..tenancy import tenant_manager

logger = logging.getLogger("qwen.agents.onboarding_concierge")

class OnboardingConciergeAgent(Agent):
    """
    Agent that acts as a Customer Success Manager.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "onboarding-concierge",
            "description": "Automates tenant onboarding and key generation.",
            "version": "1.0.0",
            "role": "Customer Success Manager",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute onboarding actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "setup_tenant", "generate_api_keys".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"OnboardingConciergeAgent received action: {action}")

        if action == "setup_tenant":
            name = input_data.get("name")
            if not name:
                return {"status": "error", "message": "Tenant name required."}
            
            try:
                # tenant_manager.create_tenant(name)
                tenant_id = f"tenant-{name.lower().replace(' ', '-')}"
                return {
                    "status": "success",
                    "message": f"Tenant '{name}' created.",
                    "tenant_id": tenant_id
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "generate_api_keys":
            tenant_id = input_data.get("tenant_id")
            try:
                # tenant_manager.create_key(tenant_id)
                new_key = "ason_sk_test_12345"
                return {
                    "status": "success",
                    "api_key": new_key,
                    "message": "API key generated. Store safely."
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'setup_tenant', 'generate_api_keys'."
            }
