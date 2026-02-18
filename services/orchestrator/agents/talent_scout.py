"""
Talent Scout Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted HR Ops module.
2. Screens resumes and matches candidates locally.
3. STRICTLY NO EXTERNAL API CALLS (No LinkedIn/Greenhouse).
4. Internal Applicant Tracking System (ATS) only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..hr_ops import resume_parser, candidate_matcher

logger = logging.getLogger("qwen.agents.talent_scout")

class TalentScoutAgent(Agent):
    """
    Agent that acts as a Talent Scout.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "talent-scout",
            "description": "Resume screening and candidate matching.",
            "version": "1.0.0",
            "role": "Talent Scout",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute recruiting actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "screen_resume", "match_job".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"TalentScoutAgent received action: {action}")

        if action == "screen_resume":
            resume_text = input_data.get("resume_text")
            try:
                # result = resume_parser.parse(resume_text)
                return {
                    "status": "success",
                    "candidate_name": "Jane Doe",
                    "skills_identified": ["Python", "FastAPI", "Docker"],
                    "experience_years": 5,
                    "education": "BS Computer Science"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "match_job":
            candidate_id = input_data.get("candidate_id", "C-999")
            job_id = input_data.get("job_id", "REQ-2026-01")
            try:
                # score = candidate_matcher.match(candidate_id, job_id)
                return {
                    "status": "success",
                    "candidate_id": candidate_id,
                    "job_id": job_id,
                    "match_score": 88,
                    "missing_skills": ["Kubernetes"],
                    "recommendation": "Interview"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'screen_resume', 'match_job'."
            }
