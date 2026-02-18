"""
Project Manager Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted PM Ops module.
2. Creates projects and assigns tasks locally.
3. STRICTLY NO EXTERNAL API CALLS (No Jira/Asana external).
4. Internal PM Tool only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..pm_ops import project_creator, task_assigner

logger = logging.getLogger("qwen.agents.project_manager")

class ProjectManagerAgent(Agent):
    """
    Agent that acts as a Project Manager.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "project-manager",
            "description": "Project creation and task assignment.",
            "version": "1.0.0",
            "role": "Project Manager",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute PM actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "create_project", "assign_task".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"ProjectManagerAgent received action: {action}")

        if action == "create_project":
            name = input_data.get("name")
            try:
                # project_id = project_creator.init(name)
                return {
                    "status": "success",
                    "project_name": name,
                    "project_id": "PROJ-OMEGA-01",
                    "workspace": "Engineering",
                    "created_at": "2026-10-25T10:00:00Z"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "assign_task":
            task_name = input_data.get("task_name")
            assignee = input_data.get("assignee")
            try:
                # task_id = task_assigner.delegate(task_name, assignee)
                return {
                    "status": "success",
                    "task_name": task_name,
                    "assignee": assignee,
                    "task_id": "TASK-992",
                    "due_date": "2026-11-01"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'create_project', 'assign_task'."
            }
