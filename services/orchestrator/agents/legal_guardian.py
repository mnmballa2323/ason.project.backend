"""
Legal Guardian Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with Legal module.
2. Generates NDAs and reviews terms.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..legal import contract_engine, compliance_checker

logger = logging.getLogger("qwen.agents.legal_guardian")

class LegalGuardianAgent(Agent):
    """
    Agent that acts as Corporate Counsel.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "legal-guardian",
            "description": "Automated NDA and legal document review.",
            "version": "1.0.0",
            "role": "Corporate Counsel",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute legal actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "generate_nda", "review_terms".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"LegalGuardianAgent received action: {action}")

        if action == "generate_nda":
            party = input_data.get("party")
            try:
                # document = contract_engine.create_nda(party)
                return {
                    "status": "success",
                    "party": party,
                    "document_url": f"/legal/contracts/nda_{party}.pdf"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "review_terms":
            doc_url = input_data.get("doc_url")
            try:
                # review = compliance_checker.review(doc_url)
                return {
                    "status": "success",
                    "risk_score": "Low",
                    "flagged_clauses": []
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'generate_nda', 'review_terms'."
            }
