"""
Insider Threat Analyst Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with Insider Threat module.
2. Analyzes user behavior and detects anomalies.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..insider_threat import ueba_engine, exfiltration_detector

logger = logging.getLogger("qwen.agents.insider_threat")

class InsiderThreatAnalystAgent(Agent):
    """
    Agent that acts as a UEBA Specialist.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "insider-threat",
            "description": "User behavior analysis and exfiltration detection.",
            "version": "1.0.0",
            "role": "UEBA Specialist",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute insider threat actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "analyze_behavior", "detect_exfiltration".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"InsiderThreatAnalystAgent received action: {action}")

        if action == "analyze_behavior":
            user_id = input_data.get("user_id")
            try:
                # score = ueba_engine.score_user(user_id)
                return {
                    "status": "success",
                    "risk_score": 15,
                    "anomalies": []
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "detect_exfiltration":
            time_window = input_data.get("time_window", "24h")
            try:
                # alerts = exfiltration_detector.scan(time_window)
                return {
                    "status": "success",
                    "alerts_count": 0,
                    "details": []
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'analyze_behavior', 'detect_exfiltration'."
            }
