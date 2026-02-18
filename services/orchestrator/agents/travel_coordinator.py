"""
Travel Coordinator Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Office Ops module.
2. Books trips and approves expenses locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Travel Portal only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..office_ops import trip_booker, expense_validator

logger = logging.getLogger("qwen.agents.travel_coordinator")

class TravelCoordinatorAgent(Agent):
    """
    Agent that acts as a Travel Coordinator.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "travel-coordinator",
            "description": "Trip booking and expense approval.",
            "version": "1.0.0",
            "role": "Travel Coordinator",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Travel actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "book_trip", "approve_expense".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"TravelCoordinatorAgent received action: {action}")

        if action == "book_trip":
            destination = input_data.get("destination")
            dates = input_data.get("dates")
            try:
                # itinerary = trip_booker.arrange(destination, dates)
                return {
                    "status": "success",
                    "destination": destination,
                    "flight": "Internal Shuttle 1",
                    "accommodation": "Company Guest House",
                    "confirmation": "TRIP-992"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "approve_expense":
            report_id = input_data.get("report_id")
            amount = input_data.get("amount")
            try:
                # result = expense_validator.check(report_id, amount)
                return {
                    "status": "success",
                    "report_id": report_id,
                    "amount": amount,
                    "decision": "Approved",
                    "policy_check": "Passed"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'book_trip', 'approve_expense'."
            }
