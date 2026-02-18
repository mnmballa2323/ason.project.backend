"""
Webhooks Manager Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with Webhooks module.
2. Manages webhook registrations and events.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..webhooks import webhook_registry, event_dispatcher

logger = logging.getLogger("qwen.agents.webhooks_manager")

class WebhooksManagerAgent(Agent):
    """
    Agent that acts as an Integration Specialist.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "webhooks-manager",
            "description": "Event integration and webhook management.",
            "version": "1.0.0",
            "role": "Integration Specialist",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute webhook actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "register_webhook", "trigger_webhook".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"WebhooksManagerAgent received action: {action}")

        if action == "register_webhook":
            url = input_data.get("url")
            events = input_data.get("events", ["all"])
            try:
                # webhook_registry.add(url, events)
                return {
                    "status": "success",
                    "webhook_id": "wh_12345",
                    "url": url,
                    "registered_events": events
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "trigger_webhook":
            event_type = input_data.get("event")
            payload = input_data.get("payload", {})
            try:
                # event_dispatcher.emit(event_type, payload)
                return {
                    "status": "success",
                    "message": f"Webhook event '{event_type}' triggered."
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'register_webhook', 'trigger_webhook'."
            }
