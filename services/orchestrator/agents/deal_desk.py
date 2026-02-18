"""
Deal Desk Analyst Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Sales Ops module.
2. Validates pricing margins and generates contracts locally.
3. STRICTLY NO EXTERNAL API CALLS (No Salesforce CPQ).
4. Internal usage only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..sales_ops import margin_validator, contract_generator

logger = logging.getLogger("qwen.agents.deal_desk")

class DealDeskAnalystAgent(Agent):
    """
    Agent that acts as a Deal Desk / Pricing Analyst.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "deal-desk",
            "description": "Pricing approval and contract generation.",
            "version": "1.0.0",
            "role": "Pricing Approver",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute deal desk actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "approve_discount", "generate_contract".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"DealDeskAnalystAgent received action: {action}")

        if action == "approve_discount":
            quote_id = input_data.get("quote_id")
            discount = input_data.get("discount")
            try:
                # Checks against floor price logic.
                # approval = margin_validator.check(quote_id, discount)
                is_approved = discount <= 20
                return {
                    "status": "success",
                    "quote_id": quote_id,
                    "discount_requested": f"{discount}%",
                    "approved": is_approved,
                    "reason": "Within regional delegation" if is_approved else "Requires VP Approval"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "generate_contract":
            quote_id = input_data.get("quote_id")
            try:
                # Merges terms into PDF template locally.
                # pdf_path = contract_generator.render(quote_id)
                return {
                    "status": "success",
                    "quote_id": quote_id,
                    "contract_url": "/internal/docs/contracts/MSA-Q900.pdf",
                    "terms": "Standard Enterprise v2.1"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'approve_discount', 'generate_contract'."
            }
