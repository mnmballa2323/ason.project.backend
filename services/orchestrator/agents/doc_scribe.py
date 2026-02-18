"""
Documentation Scribe Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with API Docs module.
2. Auto-generates specifications and documentation from code.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..api_docs import doc_generator

logger = logging.getLogger("qwen.agents.doc_scribe")

class DocScribeAgent(Agent):
    """
    Agent that acts as a Technical Writer.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "doc-scribe",
            "description": "Automated documentation. Updates specs and READMEs.",
            "version": "1.0.0",
            "role": "Technical Writer",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute documentation actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "generate_specs", "update_readme".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"DocScribeAgent received action: {action}")

        if action == "generate_specs":
            try:
                spec_path = doc_generator.generate_openapi_spec()
                return {
                    "status": "success",
                    "message": f"OpenAPI spec generated at {spec_path}",
                    "path": spec_path
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "update_readme":
            try:
                # doc_generator.update_product_docs()
                success = doc_generator.refresh_docs()
                return {
                    "status": "success",
                    "message": "Documentation refreshed based on latest code." if success else "Failed to refresh."
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'generate_specs', 'update_readme'."
            }
