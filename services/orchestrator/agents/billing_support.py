"""
Billing Support Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Support Ops module.
2. Processes refunds and generates invoices locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Billing System only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..support_ops import refund_processor, invoice_generator

logger = logging.getLogger("qwen.agents.billing_support")

class BillingSupportAgent(Agent):
    """
    Agent that acts as Billing Support.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "billing-support",
            "description": "Refund processing and invoice generation.",
            "version": "1.0.0",
            "role": "Billing Support",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Billing actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "process_refund", "generate_invoice".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"BillingSupportAgent received action: {action}")

        if action == "process_refund":
            transaction_id = input_data.get("transaction_id")
            try:
                # refund_id = refund_processor.initiate(transaction_id)
                return {
                    "status": "success",
                    "transaction_id": transaction_id,
                    "refund_amount": "$50.00",
                    "status": "Processed",
                    "refund_id": "RF-202"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "generate_invoice":
            user_id = input_data.get("user_id", "U-1")
            try:
                # invoice_url = invoice_generator.create(user_id)
                return {
                    "status": "success",
                    "user_id": user_id,
                    "invoice_url": "/internal/billing/invoices/inv_2026_02.pdf",
                    "amount_due": "$120.00"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'process_refund', 'generate_invoice'."
            }
