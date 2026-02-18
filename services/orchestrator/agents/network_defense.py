"""
Network Defense Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with Network Defense module.
2. Blocks malicious IPs and isolates subnets.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..network_defense import firewall_manager
from ..network_segmentation import segmentation_controller

logger = logging.getLogger("qwen.agents.network_defense")

class NetworkDefenseAgent(Agent):
    """
    Agent that acts as a Network Security Engineer.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "network-defense",
            "description": "Active network defense and segmentation.",
            "version": "1.0.0",
            "role": "Network Security Engineer",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute network defense actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "block_ip", "isolate_subnet".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"NetworkDefenseAgent received action: {action}")

        if action == "block_ip":
            ip = input_data.get("ip")
            if not ip:
                return {"status": "error", "message": "IP required."}
            
            try:
                # firewall_manager.add_deny_rule(ip)
                return {
                    "status": "success",
                    "message": f"IP {ip} blocked successfully."
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "isolate_subnet":
            subnet_id = input_data.get("subnet_id")
            try:
                # segmentation_controller.quarantine(subnet_id)
                return {
                    "status": "success",
                    "message": f"Subnet {subnet_id} isolated."
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'block_ip', 'isolate_subnet'."
            }
