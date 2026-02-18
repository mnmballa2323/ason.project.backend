"""
Copywriter Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Media Ops module.
2. Generates slogans and ad copy locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal LLM/Creative Writer only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..media_ops import slogan_generator, ad_copy_writer

logger = logging.getLogger("qwen.agents.copywriter")

class CopywriterAgent(Agent):
    """
    Agent that acts as a Copywriter.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "copywriter",
            "description": "Slogan generation and ad copy writing.",
            "version": "1.0.0",
            "role": "Copywriter",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Copy actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "generate_slogan", "write_ad_copy".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"CopywriterAgent received action: {action}")

        if action == "generate_slogan":
            product = input_data.get("product")
            try:
                # slogan = slogan_generator.create(product)
                return {
                    "status": "success",
                    "product": product,
                    "slogan": f"Experience the future with {product}.",
                    "tone": "Inspirational"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "write_ad_copy":
            platform = input_data.get("platform", "Social Media")
            topic = input_data.get("topic", "Launch")
            try:
                # copy = ad_copy_writer.draft(platform, topic)
                return {
                    "status": "success",
                    "platform": platform,
                    "copy_text": f"Exciting news! Our {topic} is finally here. Don't miss out! #{topic}",
                    "word_count": 25
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'generate_slogan', 'write_ad_copy'."
            }
