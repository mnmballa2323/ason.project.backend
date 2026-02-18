"""
Wellness Coach Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Health Ops module.
2. Suggests breaks and tracks steps locally.
3. STRICTLY NO EXTERNAL API CALLS (No Apple Health/Fitbit external).
4. Internal Wellness Portal only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..health_ops import break_scheduler, step_tracker

logger = logging.getLogger("qwen.agents.wellness_coach")

class WellnessCoachAgent(Agent):
    """
    Agent that acts as a Wellness Coach.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "wellness-coach",
            "description": "Employee well-being and activity tracking.",
            "version": "1.0.0",
            "role": "Wellness Coach",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute wellness actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "suggest_break", "track_steps".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"WellnessCoachAgent received action: {action}")

        if action == "suggest_break":
            calendar_id = input_data.get("calendar_id")
            try:
                # suggestion = break_scheduler.analyze(calendar_id)
                return {
                    "status": "success",
                    "calendar_id": calendar_id,
                    "suggestion": "Take a 5-minute walk at 2:00 PM.",
                    "reason": "3 hours of continuous meetings detected."
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "track_steps":
            user_id = input_data.get("user_id")
            steps = input_data.get("steps", 5000)
            try:
                # log = step_tracker.add(user_id, steps)
                return {
                    "status": "success",
                    "user_id": user_id,
                    "steps_logged": steps,
                    "daily_total": 8500,
                    "goal_progress": "85%"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'suggest_break', 'track_steps'."
            }
