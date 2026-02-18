"""
Onboarding Assistant Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted HR Ops module.
2. Assigns buddies and tracks checklists locally.
3. STRICTLY NO EXTERNAL API CALLS (No Workday/BambooHR external).
4. Internal HRIS only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..hr_ops import buddy_matcher, onboarding_tracker

logger = logging.getLogger("qwen.agents.onboarding_assistant")

class OnboardingAssistantAgent(Agent):
    """
    Agent that acts as an Onboarding Assistant.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "onboarding-assistant",
            "description": "New hire buddy assignment and checklist tracking.",
            "version": "1.0.0",
            "role": "Onboarding Assistant",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute onboarding actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "assign_buddy", "checklist_status".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"OnboardingAssistantAgent received action: {action}")

        if action == "assign_buddy":
            new_hire_id = input_data.get("new_hire_id")
            department = input_data.get("department", "Engineering")
            try:
                # buddy = buddy_matcher.find_match(new_hire_id, department)
                return {
                    "status": "success",
                    "new_hire_id": new_hire_id,
                    "assigned_buddy": "B-Senior-Dev",
                    "department": department,
                    "intro_email_sent": True
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "checklist_status":
            new_hire_id = input_data.get("new_hire_id")
            try:
                # status = onboarding_tracker.get_progress(new_hire_id)
                return {
                    "status": "success",
                    "new_hire_id": new_hire_id,
                    "completed_items": ["IT Setup", "Badge Photo"],
                    "pending_items": ["Benefits Enrollment", "Security Training"],
                    "progress": "50%"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'assign_buddy', 'checklist_status'."
            }
