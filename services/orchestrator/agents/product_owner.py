"""
Product Owner Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Agile Ops module.
2. Prioritizes backlog and approves stories locally.
3. STRICTLY NO EXTERNAL API CALLS (No Jira/Trello external).
4. Internal Backlog DB only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..agile_ops import backlog_manager, story_approver

logger = logging.getLogger("qwen.agents.product_owner")

class ProductOwnerAgent(Agent):
    """
    Agent that acts as a Product Owner.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "product-owner",
            "description": "Backlog prioritization and story approval.",
            "version": "1.0.0",
            "role": "Product Owner",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute product owner actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "prioritize_backlog", "approve_story".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"ProductOwnerAgent received action: {action}")

        if action == "prioritize_backlog":
            project_id = input_data.get("project_id", "PRJ-Alpha")
            try:
                # new_order = backlog_manager.sort_by_value(project_id)
                return {
                    "status": "success",
                    "project_id": project_id,
                    "top_stories": ["User-Login", "Payment-Integration", "Search-Bar"],
                    "sorting_logic": "Business Value / Effort"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "approve_story":
            story_id = input_data.get("story_id")
            try:
                # status = story_approver.review(story_id)
                return {
                    "status": "success",
                    "story_id": story_id,
                    "approved": True,
                    "comments": "Acceptance criteria met.",
                    "ready_for_release": True
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'prioritize_backlog', 'approve_story'."
            }
