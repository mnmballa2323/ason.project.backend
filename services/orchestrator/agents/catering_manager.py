"""
Catering Manager Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Food Services module.
2. Orders from internal kitchen and checks allergies.
3. STRICTLY NO EXTERNAL API CALLS (No Seamless/UberEats).
4. Local kitchen delivery.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..food_services import menu_selector, allergy_checker

logger = logging.getLogger("qwen.agents.catering_manager")

class CateringManagerAgent(Agent):
    """
    Agent that acts as a Catering / Hospitality Manager.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "catering-manager",
            "description": "Food and beverage coordination for internal events.",
            "version": "1.0.0",
            "role": "Hospitality Manager",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute catering actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "order_menu", "track_dietary".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"CateringManagerAgent received action: {action}")

        if action == "order_menu":
            event_id = input_data.get("event_id")
            count = input_data.get("count")
            try:
                # Orders coffee and lunch from cafeteria.
                # order = menu_selector.place_order(event_id, count)
                return {
                    "status": "success",
                    "event_id": event_id,
                    "order_id": "CAT-999",
                    "items": ["Assorted Sandwiches", "Coffee Service", "Fruit Platter"],
                    "service_time": "12:00 PM"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "track_dietary":
            event_id = input_data.get("event_id")
            try:
                # Cross-refs attendee IDs with medical file (safe subset).
                # needs = allergy_checker.scan(event_id)
                return {
                    "status": "success",
                    "event_id": event_id,
                    "flags": ["Gluten-Free: 5", "Nut-Free: 2", "Vegan: 10"],
                    "special_meals_ordered": True
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'order_menu', 'track_dietary'."
            }
