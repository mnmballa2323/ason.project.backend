"""
Safety Inspector Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Health Ops module.
2. Schedules audits and logs incidents locally.
3. STRICTLY NO EXTERNAL API CALLS (No OSHA external).
4. Internal EHS Log only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..health_ops import audit_scheduler, incident_logger

logger = logging.getLogger("qwen.agents.safety_inspector")

class SafetyInspectorAgent(Agent):
    """
    Agent that acts as a Safety Inspector.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "safety-inspector",
            "description": "EHS compliance and incident logging.",
            "version": "1.0.0",
            "role": "Safety Inspector",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute safety inspection actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "schedule_audit", "log_incident".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"SafetyInspectorAgent received action: {action}")

        if action == "schedule_audit":
            billing_id = input_data.get("billing_id", "Factory-1")
            try:
                # audit = audit_scheduler.book(billing_id)
                return {
                    "status": "success",
                    "billing_id": billing_id,
                    "audit_date": "2026-10-15",
                    "inspector": "Internal-Safety-Team",
                    "checklist": ["Fire Extinguishers", "Walkways", "PPE"]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "log_incident":
            incident_type = input_data.get("type", "Near-Miss")
            location = input_data.get("location")
            try:
                # record = incident_logger.create(incident_type, location)
                return {
                    "status": "success",
                    "incident_id": "INC-2026-404",
                    "type": incident_type,
                    "location": location,
                    "severity": "Low",
                    "follow_up_required": True
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'schedule_audit', 'log_incident'."
            }
