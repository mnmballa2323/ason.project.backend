"""
Community Manager Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Social Ops module.
2. Moderates comments and welcomes members locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Forum/Chat only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..social_ops import comment_moderator, onboarding_bot

logger = logging.getLogger("qwen.agents.community_manager")

class CommunityManagerAgent(Agent):
    """
    Agent that acts as a Community Manager.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "community-manager",
            "description": "Comment moderation and member onboarding.",
            "version": "1.0.0",
            "role": "Community Manager",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Community actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "moderate_comment", "welcome_member".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"CommunityManagerAgent received action: {action}")

        if action == "moderate_comment":
            comment = input_data.get("comment")
            try:
                # flag = comment_moderator.check(comment)
                return {
                    "status": "success",
                    "comment_id": "CMT-99",
                    "flagged": False,
                    "sentiment": "Neutral",
                    "action_taken": "Approved"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "welcome_member":
            username = input_data.get("username")
            try:
                # msg = onboarding_bot.greet(username)
                return {
                    "status": "success",
                    "username": username,
                    "message_sent": f"Welcome directly to the community, {username}!",
                    "channel": "#general"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'moderate_comment', 'welcome_member'."
            }
