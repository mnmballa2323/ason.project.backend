"""
Vulnerability Analyst Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with Vulnerability Management and SBOM modules.
2. Triggers scans and prioritizes CVEs.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..vuln_management import vuln_manager
from ..sbom import sbom_generator

logger = logging.getLogger("qwen.agents.vuln_analyst")

class VulnerabilityAnalystAgent(Agent):
    """
    Agent that acts as a Security Engineer / Vuln Manager.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "vuln-analyst",
            "description": "Automated vulnerability management. Scans code/artifacts and manages SBOMs.",
            "version": "1.0.0",
            "role": "Security Engineer",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute vulnerability analysis actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "scan_cves", "analyze_sbom", "get_risk_report".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"VulnerabilityAnalystAgent received action: {action}")

        if action == "scan_cves":
            artifact = input_data.get("artifact_path", "current_build")
            try:
                # vuln_manager.scan(artifact)
                report = vuln_manager.trigger_scan(artifact)
                return {
                    "status": "success",
                    "cve_count": len(report.get("findings", [])),
                    "data": report
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "analyze_sbom":
            # Check SBOM for policy violations
            try:
                sbom = sbom_generator.get_latest_sbom()
                analysis = vuln_manager.analyze_sbom(sbom)
                return {
                    "status": "success",
                    "data": analysis
                }
            except Exception as e:
                 return {"status": "error", "message": str(e)}

        elif action == "get_risk_report":
            try:
                report = vuln_manager.get_top_risks()
                return {
                    "status": "success",
                    "data": report
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'scan_cves', 'analyze_sbom', 'get_risk_report'."
            }
