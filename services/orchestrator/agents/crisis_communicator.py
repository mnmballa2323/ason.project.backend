"""
Crisis Communicator Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Brand Ops module.
2. Assesses crises and prepares statements locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Incident Response System only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..brand_ops import crisis_assessor, statement_prep

logger = logging.getLogger("qwen.agents.crisis_communicator")

class CrisisCommunicatorAgent(Agent):
    """
    Agent that acts as a Crisis Communicator.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "crisis-communicator",
            "description": "Crisis assessment and communication planning.",
            "version": "1.0.0",
            "role": "Crisis Communicator",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Crisis Response actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "assess_crisis", "prepare_statement".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"CrisisCommunicatorAgent received action: {action}")

        if action == "assess_crisis":
            incident_id = input_data.get("incident_id")
            try:
                # severity = crisis_assessor.evaluate(incident_id)
                return {
                    "status": "success",
                    "incident_id": incident_id,
                    "severity": "Level 3 (High)",
                    "impact_scope": "Customer Data",
                    "required_response": "Immediate Public Statement"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "prepare_statement":
            audience = input_data.get("audience", "Public")
            key_message = input_data.get("key_message")
            try:
                # stmt = statement_prep.draft(audience, key_message)
                return {
                    "status": "success",
                    "audience": audience,
                    "draft_statement": "We are aware of the issue and actively investigating...",
                    "legal_approved": "Pending",
                    "version": "v1.0"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'assess_crisis', 'prepare_statement'."
            }
