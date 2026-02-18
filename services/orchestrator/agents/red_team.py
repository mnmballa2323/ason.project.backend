"""
Red Team Operator Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Unified interface for Offensive Security.
2. Triggers AI Red Teaming (jailbreaks, prompt injection).
3. Triggers Penetration Testing (OWASP Top 10).
"""

import logging
from typing import Dict, Any
from . import Agent
from ..ai_redteam import ai_redteam
from ..pentest_framework import pentest_framework

logger = logging.getLogger("qwen.agents.red_team")

class RedTeamOperator(Agent):
    """
    Agent that acts as an Offensive Security Engineer.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "red-team",
            "description": "Unified offensive security engine. Runs AI red teaming and conventional penetration tests.",
            "version": "1.0.0",
            "role": "Offensive Security Engineer",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute offensive security operations.
        
        Args:
            input_data: Must contain "action" (str).
                        Supported actions: "run_ai_redteam", "run_pentest", "get_security_posture".
            context: Optional.
            
        Returns:
            Dict containing the test results.
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"RedTeamOperator received action: {action}")

        if action == "run_ai_redteam":
            # Run AI-specific attacks (Jailbreaks, Prompt Injection)
            try:
                results = ai_redteam.run_full_suite()
                return {
                    "status": "success",
                    "type": "ai_redteam",
                    "data": results,
                    "summary": f"Completed {results['summary']['total_tests']} tests. Defense Rate: {results['summary']['defense_rate']}%"
                }
            except Exception as e:
                logger.error(f"AI Red Team run failed: {e}")
                return {"status": "error", "message": str(e)}

        elif action == "run_pentest":
            # Run OWASP Top 10 checks
            try:
                results = pentest_framework.run_all()
                return {
                    "status": "success",
                    "type": "pentest",
                    "data": results,
                    "summary": f"Completed {results['total_tests']} tests. Score: {results['score']}%"
                }
            except Exception as e:
                logger.error(f"Pentest run failed: {e}")
                return {"status": "error", "message": str(e)}

        elif action == "get_security_posture":
            # high-level stats from both engines
            try:
                ai_stats = ai_redteam.get_stats()
                # PenTestFramework doesn't have a get_stats method, so we'll just run it or implement one later.
                # For now, we'll just return AI stats and available pentest count.
                pentest_coverage = pentest_framework.get_owasp_coverage()
                
                return {
                    "status": "success",
                    "data": {
                        "ai_redteam": ai_stats,
                        "pentest_coverage": pentest_coverage
                    }
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'run_ai_redteam', 'run_pentest', 'get_security_posture'."
            }
