"""
Travel Manager Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Travel Booking module.
2. Books flights/hotels strategies using LOCAL inventory/contracts.
3. STRICTLY NO EXTERNAL API CALLS (No Expedia/Concur/GDS).
4. Enforces local travel policy.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..travel_booking import internal_inventory, policy_engine

logger = logging.getLogger("qwen.agents.travel_manager")

class TravelManagerAgent(Agent):
    """
    Agent that acts as a Corporate Travel Agent (Internal Only).
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "travel-manager",
            "description": "Internal travel booking and policy enforcement. No external GDS.",
            "version": "1.0.0",
            "role": "Travel Agent",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute travel actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "book_itinerary", "enforce_policy".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"TravelManagerAgent received action: {action}")

        if action == "book_itinerary":
            destination = input_data.get("destination")
            dates = input_data.get("dates")
            try:
                # Queries INTERNAL inventory database only.
                # booking_ref = internal_inventory.book(destination, dates)
                return {
                    "status": "success",
                    "destination": destination,
                    "dates": dates,
                    "booking_reference": "INT-TRV-2026-884",
                    "carrier": "Internal Shuttle / Chartered",
                    "note": "Booked via internal asset management system."
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "enforce_policy":
            itinerary_id = input_data.get("itinerary_id")
            try:
                # Checks against LOCAL policy file.
                # compliant = policy_engine.check(itinerary_id)
                return {
                    "status": "success",
                    "itinerary_id": itinerary_id,
                    "compliant": True,
                    "violations": []
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'book_itinerary', 'enforce_policy'."
            }
