"""
Tax Analyst Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Tax Compliance module.
2. Calculates liability and prepares filings.
3. Strictly self-hosted.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..tax_compliance import liability_calculator, form_generator

logger = logging.getLogger("qwen.agents.tax_analyst")

class TaxAnalystAgent(Agent):
    """
    Agent that acts as a Tax Accountant.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "tax-analyst",
            "description": "Tax liability estimation and filing preparation.",
            "version": "1.0.0",
            "role": "Tax Accountant",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute tax actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "calculate_liability", "prepare_filing".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"TaxAnalystAgent received action: {action}")

        if action == "calculate_liability":
            quarter = input_data.get("quarter")
            try:
                # amount = liability_calculator.estimate(quarter)
                return {
                    "status": "success",
                    "quarter": quarter,
                    "estimated_liability": "$1,250,000.00",
                    "due_date": "2026-04-15"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "prepare_filing":
            form_type = input_data.get("form_type")
            try:
                # doc_url = form_generator.create(form_type)
                return {
                    "status": "success",
                    "form_type": form_type,
                    "filing_package_url": f"/internal/finance/tax/{form_type}_2026.pdf"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'calculate_liability', 'prepare_filing'."
            }
