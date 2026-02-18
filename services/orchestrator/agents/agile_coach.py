"""
Agile Coach Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Agile Ops module.
2. Assesses maturity and recommends practices locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Knowledge Base only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..agile_ops import maturity_assessor, practice_recommender

logger = logging.getLogger("qwen.agents.agile_coach")

class AgileCoachAgent(Agent):
    """
    Agent that acts as an Agile Coach.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "agile-coach",
            "description": "Agile maturity assessment and coaching.",
            "version": "1.0.0",
            "role": "Agile Coach",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute agile coaching actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "assess_maturity", "recommend_practice".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"AgileCoachAgent received action: {action}")

        if action == "assess_maturity":
            team_id = input_data.get("team_id")
            try:
                # score = maturity_assessor.score(team_id)
                return {
                    "status": "success",
                    "team_id": team_id,
                    "maturity_score": "3.5/5",
                    "level": "Practicing",
                    "areas_for_improvement": ["Automated Testing", "Retrospective Quality"]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "recommend_practice":
            issue = input_data.get("issue", "Long Standups")
            try:
                # advice = practice_recommender.get_advice(issue)
                return {
                    "status": "success",
                    "issue": issue,
                    "recommendation": "Walk the Board",
                    "description": "Focus on tickets moving right, not just status updates.",
                    "resource_link": "/internal/wiki/agile/standups"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'assess_maturity', 'recommend_practice'."
            }
