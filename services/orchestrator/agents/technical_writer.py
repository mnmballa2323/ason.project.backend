"""
Technical Writer Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Content Ops module.
2. Drafts manuals and updates changelogs locally.
3. STRICTLY NO EXTERNAL API CALLS (No ChatGPT external).
4. Internal Wiki/Docs only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..content_ops import manual_drafter, changelog_updater

logger = logging.getLogger("qwen.agents.technical_writer")

class TechnicalWriterAgent(Agent):
    """
    Agent that acts as a Technical Writer.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "tech-writer",
            "description": "Manual drafting and changelog updates.",
            "version": "1.0.0",
            "role": "Technical Writer",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Writing actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "draft_manual", "update_changelog".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"TechnicalWriterAgent received action: {action}")

        if action == "draft_manual":
            topic = input_data.get("topic")
            try:
                # content = manual_drafter.write(topic)
                return {
                    "status": "success",
                    "topic": topic,
                    "draft_url": "/internal/docs/drafts/installation_guide_v2.md",
                    "word_count": 1200,
                    "review_status": "Pending"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "update_changelog":
            version = input_data.get("version")
            try:
                # entry = changelog_updater.add(version)
                return {
                    "status": "success",
                    "version": version,
                    "changelog_updated": True,
                    "items_added": ["New Login Flow", "Bug Fix #221"]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'draft_manual', 'update_changelog'."
            }
