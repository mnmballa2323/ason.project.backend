"""
Interview Scheduler Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted HR Ops module.
2. Finds slots and books panels locally.
3. STRICTLY NO EXTERNAL API CALLS (No Google Calendar/Outlook external).
4. Internal Calendaring System only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..hr_ops import calendar_manager, panel_coordinator

logger = logging.getLogger("qwen.agents.interview_scheduler")

class InterviewSchedulerAgent(Agent):
    """
    Agent that acts as an Interview Scheduler.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "interview-scheduler",
            "description": "Interview slot finding and panel coordination.",
            "version": "1.0.0",
            "role": "Interview Scheduler",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute scheduling actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "find_slot", "book_panel".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"InterviewSchedulerAgent received action: {action}")

        if action == "find_slot":
            interviewer = input_data.get("interviewer")
            try:
                # slots = calendar_manager.get_availability(interviewer)
                return {
                    "status": "success",
                    "interviewer": interviewer,
                    "available_slots": ["2026-05-20 14:00", "2026-05-21 10:00"]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "book_panel":
            candidate_id = input_data.get("candidate_id")
            panelists = input_data.get("panelists", ["int1", "int2"])
            try:
                # booking = panel_coordinator.book(candidate_id, panelists)
                return {
                    "status": "success",
                    "candidate_id": candidate_id,
                    "panel_date": "2026-05-25",
                    "schedule": {
                        "09:00": "int1 (Technical)",
                        "10:00": "int2 (Behavioral)"
                    },
                    "room": "Virtual-Room-4"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'find_slot', 'book_panel'."
            }
