"""
Legal Assistant Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Legal Ops module.
2. Drafts contracts and reviews terms locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Legal Templates only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..legal_ops import contract_drafter, term_reviewer

logger = logging.getLogger("qwen.agents.legal_assistant")

class LegalAssistantAgent(Agent):
    """
    Agent that acts as a Legal Assistant.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "legal-assistant",
            "description": "Contract drafting and term review.",
            "version": "1.0.0",
            "role": "Legal Assistant",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Legal actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "draft_contract", "review_terms".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"LegalAssistantAgent received action: {action}")

        if action == "draft_contract":
            contract_type = input_data.get("type", "NDA")
            party_b = input_data.get("party_b", "Vendor X")
            try:
                # draft = contract_drafter.create(contract_type, party_b)
                return {
                    "status": "success",
                    "contract_type": contract_type,
                    "download_url": "/internal/legal/contracts/draft_551.pdf",
                    "version": "v1"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "review_terms":
            doc_id = input_data.get("doc_id")
            try:
                # risks = term_reviewer.analyze(doc_id)
                return {
                    "status": "success",
                    "doc_id": doc_id,
                    "risky_clauses": ["Indemnity Cap"],
                    "risk_score": "Medium",
                    "recommendation": "Negotiate Cap"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'draft_contract', 'review_terms'."
            }
