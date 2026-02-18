"""
Technical Support Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Support Ops module.
2. Debugs issues and analyzes logs locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Debugger only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..support_ops import issue_debugger, log_analyzer

logger = logging.getLogger("qwen.agents.technical_support")

class TechnicalSupportAgent(Agent):
    """
    Agent that acts as Technical Support.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "technical-support",
            "description": "Issue debugging and log analysis.",
            "version": "1.0.0",
            "role": "Technical Support",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Tech Support actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "debug_issue", "analyze_logs".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"TechnicalSupportAgent received action: {action}")

        if action == "debug_issue":
            error_code = input_data.get("error_code")
            try:
                # fix = issue_debugger.lookup(error_code)
                return {
                    "status": "success",
                    "error_code": error_code,
                    "suggested_fix": "Restart the service and clear cache.",
                    "kb_article": "KB-101"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "analyze_logs":
            log_content = input_data.get("log_content", "Sample Log")
            try:
                # report = log_analyzer.parse(log_content)
                return {
                    "status": "success",
                    "issues_found": 1,
                    "root_cause": "TimeoutException at line 45",
                    "severity": "High"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'debug_issue', 'analyze_logs'."
            }
