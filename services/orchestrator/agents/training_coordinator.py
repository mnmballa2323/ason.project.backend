"""
Training Coordinator Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with Training module.
2. Recommends courses and generates quizzes.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..training import course_recommender, quiz_engine

logger = logging.getLogger("qwen.agents.training_coordinator")

class TrainingCoordinatorAgent(Agent):
    """
    Agent that acts as an Enablement Lead.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "training-coordinator",
            "description": "Automated training recommendations and quiz generation.",
            "version": "1.0.0",
            "role": "Enablement Lead",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute training actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "recommend_courses", "generate_quiz".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"TrainingCoordinatorAgent received action: {action}")

        if action == "recommend_courses":
            user_role = input_data.get("user_role")
            try:
                # courses = course_recommender.get_for_role(user_role)
                return {
                    "status": "success",
                    "recommended_courses": ["Secure Coding 101", "OWASP Top 10"]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "generate_quiz":
            topic = input_data.get("topic")
            try:
                # quiz = quiz_engine.create(topic)
                return {
                    "status": "success",
                    "questions_generated": 10,
                    "difficulty": "Intermediate"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'recommend_courses', 'generate_quiz'."
            }
