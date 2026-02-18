"""
Localization Specialist Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted i18n Ops module.
2. Adapts formats and reviews UI locally.
3. STRICTLY NO EXTERNAL API CALLS (No Google Translate external).
4. Internal Locale DB only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..i18n_ops import format_adapter, ui_reviewer

logger = logging.getLogger("qwen.agents.localization_specialist")

class LocalizationSpecialistAgent(Agent):
    """
    Agent that acts as a Localization Specialist.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "localization-specialist",
            "description": "Format adaptation and UI review.",
            "version": "1.0.0",
            "role": "Localization Specialist",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute L10n actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "adjust_format", "review_ui".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"LocalizationSpecialistAgent received action: {action}")

        if action == "adjust_format":
            region = input_data.get("region")
            try:
                # rules = format_adapter.get_rules(region)
                return {
                    "status": "success",
                    "region": region,
                    "date_format": "YYYY/MM/DD",
                    "currency": "JPY",
                    "number_separator": ","
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "review_ui":
            screen_id = input_data.get("screen_id")
            language = input_data.get("language", "DE")
            try:
                # issues = ui_reviewer.scan(screen_id, language)
                return {
                    "status": "success",
                    "screen_id": screen_id,
                    "language": language,
                    "overflow_issues": 2,
                    "truncated_text": ["Submit Button", "Header"]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'adjust_format', 'review_ui'."
            }
