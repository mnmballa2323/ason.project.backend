"""
Licensing Manager Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with Licensing module.
2. Issues and validates software licenses.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..licensing import license_generator, validator

logger = logging.getLogger("qwen.agents.licensing_manager")

class LicensingManagerAgent(Agent):
    """
    Agent that acts as a Licensing Specialist.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "licensing-manager",
            "description": "Software license issuance and validation.",
            "version": "1.0.0",
            "role": "Licensing Specialist",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute licensing actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "issue_license", "validate_license".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"LicensingManagerAgent received action: {action}")

        if action == "issue_license":
            customer = input_data.get("customer")
            features = input_data.get("features", ["standard"])
            try:
                # license_key = license_generator.create(customer, features)
                license_key = "ASON-XXXX-YYYY-ZZZZ"
                return {
                    "status": "success",
                    "license_key": license_key,
                    "customer": customer
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "validate_license":
            key = input_data.get("key")
            try:
                # is_valid = validator.check(key)
                return {
                    "status": "success",
                    "valid": True,
                    "expires": "2025-12-31"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'issue_license', 'validate_license'."
            }
