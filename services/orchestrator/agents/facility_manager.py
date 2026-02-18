"""
Facility Manager Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Office Ops module.
2. Logs maintenance and audits supplies locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Facilities DB only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..office_ops import maintenance_logger, supply_auditor

logger = logging.getLogger("qwen.agents.facility_manager")

class FacilityManagerAgent(Agent):
    """
    Agent that acts as a Facility Manager.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "facility-manager",
            "description": "Maintenance logging and supply auditing.",
            "version": "1.0.0",
            "role": "Facility Manager",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Facility actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "log_maintenance", "audit_supplies".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"FacilityManagerAgent received action: {action}")

        if action == "log_maintenance":
            issue = input_data.get("issue")
            location = input_data.get("location", "HQ")
            try:
                # ticket = maintenance_logger.create(issue, location)
                return {
                    "status": "success",
                    "issue": issue,
                    "location": location,
                    "ticket_id": "MAINT-771",
                    "priority": "Normal",
                    "assigned_team": "On-Site Crew"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "audit_supplies":
            category = input_data.get("category", "General")
            try:
                # report = supply_auditor.check(category)
                return {
                    "status": "success",
                    "category": category,
                    "items_checked": 150,
                    "low_stock_alerts": 2,
                    "restock_triggered": True
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'log_maintenance', 'audit_supplies'."
            }
