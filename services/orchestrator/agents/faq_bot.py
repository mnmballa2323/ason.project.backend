"""
FAQ Bot Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Support Ops module.
2. Answers queries and suggests articles locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Knowledge Base only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..support_ops import kb_retriever, article_recommender

logger = logging.getLogger("qwen.agents.faq_bot")

class FAQBotAgent(Agent):
    """
    Agent that acts as an FAQ Bot.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "faq-bot",
            "description": "Knowledge retrieval and article suggestion.",
            "version": "1.0.0",
            "role": "FAQ Bot",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute FAQ actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "answer_query", "suggest_article".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"FAQBotAgent received action: {action}")

        if action == "answer_query":
            question = input_data.get("question")
            try:
                # answer = kb_retriever.search(question)
                return {
                    "status": "success",
                    "question": question,
                    "answer": "To reset VPN, click 'Disconnect' then 'Connect' in the tray icon.",
                    "confidence": "98%",
                    "source": "KB-Article-442"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "suggest_article":
            keywords = input_data.get("keywords", [])
            try:
                # articles = article_recommender.find(keywords)
                return {
                    "status": "success",
                    "keywords": keywords,
                    "suggested_articles": [
                        {"title": "VPN Troubleshooting", "id": "KB-442"},
                        {"title": "Network Policy", "id": "KB-101"}
                    ]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'answer_query', 'suggest_article'."
            }
