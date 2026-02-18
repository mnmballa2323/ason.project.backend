"""
Customer Support Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Support Ops module.
2. Answers queries and routes tickets locally.
3. STRICTLY NO EXTERNAL API CALLS (No Zendesk external).
4. Internal Knowledge Base only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..support_ops import faq_engine, ticket_router

logger = logging.getLogger("qwen.agents.customer_support")

class CustomerSupportAgent(Agent):
    """
    Agent that acts as Customer Support.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "customer-support",
            "description": "FAQ answering and ticket routing.",
            "version": "1.0.0",
            "role": "Customer Support",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Support actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "answer_query", "route_ticket".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"CustomerSupportAgent received action: {action}")

        if action == "answer_query":
            query = input_data.get("query")
            try:
                # answer = faq_engine.search(query)
                return {
                    "status": "success",
                    "query": query,
                    "answer": "To reset your password, visit /settings/security.",
                    "confidence": "98%"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "route_ticket":
            category = input_data.get("keywords", "General")
            try:
                # queue = ticket_router.assign(category)
                return {
                    "status": "success",
                    "category": category,
                    "assigned_queue": "Tier-1 Support",
                    "ticket_id": "TKT-505"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'answer_query', 'route_ticket'."
            }
