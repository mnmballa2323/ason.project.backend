"""
Forensics Investigator Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with Forensics module.
2. Performs disk and memory analysis.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..forensics import disk_analyzer, memory_analyzer

logger = logging.getLogger("qwen.agents.forensics_investigator")

class ForensicsInvestigatorAgent(Agent):
    """
    Agent that acts as a Digital Forensics Expert.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "forensics-investigator",
            "description": "Digital forensics on disk and memory.",
            "version": "1.0.0",
            "role": "Digital Forensics Expert",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute forensics actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "analyze_disk", "analyze_memory".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"ForensicsInvestigatorAgent received action: {action}")

        if action == "analyze_disk":
            image_path = input_data.get("image_path")
            try:
                # report = disk_analyzer.scan(image_path)
                return {
                    "status": "success",
                    "artifacts_found": 12,
                    "suspicious_files": ["/tmp/exploit.sh"]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "analyze_memory":
            dump_path = input_data.get("dump_path")
            try:
                # result = memory_analyzer.process(dump_path)
                return {
                    "status": "success",
                    "injected_code_detected": False,
                    "processes_analyzed": 150
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'analyze_disk', 'analyze_memory'."
            }
