"""
Threat Hunter Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with ThreatHuntingEngine.
2. Triggers IOC sweeps and hypothesis-driven hunts.
3. Analyzes threat stats.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..threat_hunting import threat_hunting_engine

logger = logging.getLogger("qwen.agents.threat_hunter")

class ThreatHunterAgent(Agent):
    """
    Agent that acts as a Defensive Security Analyst / Threat Hunter.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "threat-hunter",
            "description": "Proactive threat hunting. Scans for IOCs and behavioral anomalies.",
            "version": "1.0.0",
            "role": "Defensive Security Analyst",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute threat hunting actions.
        
        Args:
            input_data: Must contain "action" (str).
                        Supported actions: "hunt_iocs", "get_stats", "list_hunts".
            context: Optional.
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"ThreatHunterAgent received action: {action}")

        if action == "hunt_iocs":
            # In a real scenario, we'd pass actual data or a data source. 
            # For this agent, we'll simulate a sweep of recent logs.
            target_data = input_data.get("data", "Simulated log stream for verification...")
            hits = threat_hunting_engine.sweep(target_data, context="agent-sweep")
            
            return {
                "status": "success",
                "action": "hunt_iocs",
                "ioc_hits": len(hits),
                "hits_details": hits
            }

        elif action == "get_stats":
            try:
                stats = threat_hunting_engine.get_stats()
                return {
                    "status": "success",
                    "data": stats
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "list_hunts":
             # This would list active human/agent hunts
            try:
                hunts = threat_hunting_engine.get_stats().get("hunts", [])
                return {
                    "status": "success",
                    "data": hunts
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'hunt_iocs', 'get_stats', 'list_hunts'."
            }
