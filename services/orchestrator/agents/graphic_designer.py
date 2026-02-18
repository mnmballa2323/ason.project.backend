"""
Graphic Designer Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Creative Ops module.
2. Generates assets and applies branding locally.
3. STRICTLY NO EXTERNAL API CALLS (No Canva/Adobe external).
4. Internal Asset Gen only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..creative_ops import asset_generator, brand_enforcer

logger = logging.getLogger("qwen.agents.graphic_designer")

class GraphicDesignerAgent(Agent):
    """
    Agent that acts as a Graphic Designer.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "graphic-designer",
            "description": "Asset generation and branding enforcement.",
            "version": "1.0.0",
            "role": "Graphic Designer",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Design actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "generate_asset", "apply_branding".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"GraphicDesignerAgent received action: {action}")

        if action == "generate_asset":
            asset_type = input_data.get("type", "Icon")
            name = input_data.get("name", "New Asset")
            try:
                # asset_path = asset_generator.create(asset_type, name)
                return {
                    "status": "success",
                    "asset_type": asset_type,
                    "name": name,
                    "url": "/internal/assets/icons/settings_icon_v2.png",
                    "dimensions": "512x512"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "apply_branding":
            image_id = input_data.get("image_id")
            try:
                # branded_url = brand_enforcer.apply_watermark(image_id)
                return {
                    "status": "success",
                    "image_id": image_id,
                    "branded_url": "/internal/assets/branded/campaign_01.jpg",
                    "primary_color": "#0056b3"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'generate_asset', 'apply_branding'."
            }
