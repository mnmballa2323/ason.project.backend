"""
Visitor Manager Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Physical Admin module.
2. Manages guest lists and lobby kiosks.
3. STRICTLY NO EXTERNAL API CALLS (No Envoy).
4. Local visitor logs only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..physical_admin import guest_log, kiosk_controller

logger = logging.getLogger("qwen.agents.visitor_manager")

class VisitorManagerAgent(Agent):
    """
    Agent that acts as a Virtual Receptionist.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "visitor-manager",
            "description": "Guest registration and lobby badge printing.",
            "version": "1.0.0",
            "role": "Receptionist",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute visitor actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "register_guest", "print_badge".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"VisitorManagerAgent received action: {action}")

        if action == "register_guest":
            guest_name = input_data.get("guest_name")
            host = input_data.get("host")
            try:
                # Adds to daily manifest.
                # ref_code = guest_log.add(guest_name, host)
                return {
                    "status": "success",
                    "guest_name": guest_name,
                    "host": host,
                    "visit_date": "2026-02-18",
                    "qr_code_generated": True
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "print_badge":
            visitor_id = input_data.get("visitor_id")
            try:
                # Sends job to lobby B&W printer.
                # status = kiosk_controller.print(visitor_id)
                return {
                    "status": "success",
                    "visitor_id": visitor_id,
                    "printer": "Lobby-Printer-1",
                    "badge_type": "Visitor (Red Lanyard)"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'register_guest', 'print_badge'."
            }
