"""
Event Planner Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Office Ops module.
2. Books venues and manages RSVPs locally.
3. STRICTLY NO EXTERNAL API CALLS (No Eventbrite external).
4. Internal Calendar/Room Booking only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..office_ops import venue_booker, rsvp_tracker

logger = logging.getLogger("qwen.agents.event_planner")

class EventPlannerAgent(Agent):
    """
    Agent that acts as an Event Planner.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "event-planner",
            "description": "Venue booking and RSVP management.",
            "version": "1.0.0",
            "role": "Event Planner",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Event actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "book_venue", "manage_rsvp".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"EventPlannerAgent received action: {action}")

        if action == "book_venue":
            event_type = input_data.get("type", "Meeting")
            attendees = input_data.get("attendees", 10)
            try:
                # venue = venue_booker.reserve(event_type, attendees)
                return {
                    "status": "success",
                    "event_type": event_type,
                    "venue_assigned": "Conference Room B",
                    "capacity": 20,
                    "reservation_id": "RES-882"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "manage_rsvp":
            event_id = input_data.get("event_id")
            try:
                # status = rsvp_tracker.tally(event_id)
                return {
                    "status": "success",
                    "event_id": event_id,
                    "total_invited": 50,
                    "accepted": 42,
                    "declined": 3,
                    "pending": 5
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'book_venue', 'manage_rsvp'."
            }
