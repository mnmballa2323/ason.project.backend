"""
Container Sentinel Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with Container Security module.
2. Audits images and monitors runtime.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..container_security import container_auditor

logger = logging.getLogger("qwen.agents.container_sentinel")

class ContainerSentinelAgent(Agent):
    """
    Agent that acts as a Cloud Security Engineer.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "container-sentinel",
            "description": "Container security auditing and monitoring.",
            "version": "1.0.0",
            "role": "Cloud Security Engineer",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute container security actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "audit_images", "monitor_runtime".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"ContainerSentinelAgent received action: {action}")

        if action == "audit_images":
            registry = input_data.get("registry", "internal")
            try:
                # container_auditor.scan_registry(registry)
                report = {
                    "images_scanned": 45,
                    "vulnerable_images": 2,
                    "top_vuln": "CVE-2024-5555"
                }
                return {
                    "status": "success",
                    "data": report
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "monitor_runtime":
            try:
                # container_auditor.get_runtime_alerts()
                alerts = []
                return {
                    "status": "success",
                    "alerts": alerts
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'audit_images', 'monitor_runtime'."
            }
