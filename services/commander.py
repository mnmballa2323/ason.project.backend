"""
NLOps Commander — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Simulates Ason-7B-Chat acting as an operator agent.
Translates Natural Language commands into System Actions (Function Calling).
"""
import logging
import re
from typing import Dict, Any

from services.safety_guard import safety_guard
from services.safety_guard import safety_guard
from services.dr_manager import dr_manager
from services.self_healing import self_healing
from services.cloud_status import cloud_status
from services.memory import memory_engine

logger = logging.getLogger("qwen.commander")

class NLOpsCommander:
    """
    The Commander.
    "I speak for the machines."
    """
    
    def execute_command(self, user_prompt: str) -> str:
        """
        Process a natural language command.
        """
        # 1. Safety Check
        is_safe, refusal = safety_guard.validate_input(user_prompt)
        if not is_safe:
            return refusal

        # 2. Intent Recognition (Simulated Ason-7B Zero-Shot Classification)
        prompt_lower = user_prompt.lower()
        
        # RAG Context: Check if we have relevant history
        context = memory_engine.retrieve(prompt_lower, limit=1)
        context_str = f"Context: {context[0]['content']}" if context else ""
        
        if "flee" in prompt_lower or "evacuate" in prompt_lower or "failover" in prompt_lower:
            return self._handle_dr_intent(prompt_lower)
            
        elif "status" in prompt_lower or "report" in prompt_lower or "health" in prompt_lower:
            return self._handle_status_intent()
            
        elif "fix" in prompt_lower or "repair" in prompt_lower or "heal" in prompt_lower:
            return self._handle_healing_intent(prompt_lower)
            
        else:
            return "I didn't understand that command. Try 'Evacuate US-East' or 'System Status'."

    def _handle_dr_intent(self, prompt: str) -> str:
        # Extract target if possible (simple heuristic)
        region = "us-east" # Default for demo
        if "eu" in prompt:
            region = "eu-central"
            
        # Call DR Manager
        success = dr_manager.initiate_failover(reason=f"Operator Command: {prompt}")
        if success:
            return f"✅ Affirmative. Initiating emergency failover sequence for {region}."
        else:
            return f"⚠️ Unable to failover. Check DR logs for details (possibly already active)."

    def _handle_status_intent(self) -> str:
        report = cloud_status.get_status_report()
        healthy = report.get("healthy_clouds", 0)
        total = report.get("total_clouds", 0)
        return f"📊 System Status: {healthy}/{total} Clouds Operational. Global uptime is {report.get('global_uptime')}."

    def _handle_healing_intent(self, prompt: str) -> str:
        # Extract target
        target = "unknown-service"
        if "db" in prompt: target = "primary-db"
        elif "api" in prompt: target = "api-gateway"
        
        self_healing.trigger_remediation(target, "Manual Intervention")
        return f"🔧 Dispatching Self-Healing nanoswarms to fix {target}."

commander = NLOpsCommander()
