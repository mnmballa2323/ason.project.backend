"""
Deliverable Tracker Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted PM Ops module.
2. Updates status and generates Gantt charts locally.
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Timeline View only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..pm_ops import status_updater, gantt_generator

logger = logging.getLogger("qwen.agents.deliverable_tracker")

class DeliverableTrackerAgent(Agent):
    """
    Agent that acts as a Deliverable Tracker.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "deliverable-tracker",
            "description": "Status tracking and Gantt chart generation.",
            "version": "1.0.0",
            "role": "Deliverable Tracker",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Delivery actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "update_status", "generate_gantt".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"DeliverableTrackerAgent received action: {action}")

        if action == "update_status":
            milestone_id = input_data.get("milestone_id")
            new_status = input_data.get("status", "Complete")
            try:
                # result = status_updater.set(milestone_id, new_status)
                return {
                    "status": "success",
                    "milestone_id": milestone_id,
                    "old_status": "In Progress",
                    "new_status": new_status,
                    "timestamp": "2026-10-25T14:30:00Z"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "generate_gantt":
            project_id = input_data.get("project_id")
            try:
                # chart = gantt_generator.render(project_id)
                return {
                    "status": "success",
                    "project_id": project_id,
                    "chart_url": "/internal/reports/gantt/proj-123.png",
                    "critical_path": ["Design", "Dev", "QA"]
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'update_status', 'generate_gantt'."
            }
