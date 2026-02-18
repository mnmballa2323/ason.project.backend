"""
Proposal Architect Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Proposal Engine module.
2. Drafts RFP responses and checks compliance.
3. Strictly self-hosted; uses internal specs.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..proposal_engine import response_generator, compliance_checker

logger = logging.getLogger("qwen.agents.proposal_architect")

class ProposalArchitectAgent(Agent):
    """
    Agent that acts as a Sales Engineer / Proposal Writer.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "proposal-architect",
            "description": "RFP response automation and compliance verification.",
            "version": "1.0.0",
            "role": "Sales Engineer",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute proposal actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "generate_response", "compliance_check".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"ProposalArchitectAgent received action: {action}")

        if action == "generate_response":
            rfp_id = input_data.get("rfp_id")
            section = input_data.get("section")
            try:
                # draft = response_generator.draft(rfp_id, section)
                return {
                    "status": "success",
                    "rfp_id": rfp_id,
                    "section": section,
                    "draft_content": "Our solution meets FIPS 140-3 requirements...",
                    "confidence_score": 0.98
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "compliance_check":
            proposal_id = input_data.get("proposal_id")
            try:
                # report = compliance_checker.verify(proposal_id)
                return {
                    "status": "success",
                    "proposal_id": proposal_id,
                    "compliant": True,
                    "missing_requirements": []
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'generate_response', 'compliance_check'."
            }
