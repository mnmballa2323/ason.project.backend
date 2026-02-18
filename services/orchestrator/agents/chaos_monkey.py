"""
Chaos Monkey Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted DevOps Ops module.
2. Terminates instances and injects latency locally (Simulated).
3. STRICTLY NO EXTERNAL API CALLS.
4. Internal Staging Environment only.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..devops_ops import chaos_injector

logger = logging.getLogger("qwen.agents.chaos_monkey")

class ChaosMonkeyAgent(Agent):
    """
    Agent that acts as a Chaos Monkey.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "chaos-monkey",
            "description": "Resilience testing and fault injection.",
            "version": "1.0.0",
            "role": "Chaos Monkey",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute Chaos actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "terminate_instance", "inject_latency".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"ChaosMonkeyAgent received action: {action}")

        if action == "terminate_instance":
            target = input_data.get("target")
            env = input_data.get("env", "staging")
            if env == "production":
                 return {"status": "error", "message": "Chaos Monkey is disabled in PRODUCTION."}
            try:
                # result = chaos_injector.kill_node(target)
                return {
                    "status": "success",
                    "target": target,
                    "action": "Force Terminate",
                    "result": "Node unreachable",
                    "recovery_time": "Expected < 2m"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "inject_latency":
            service = input_data.get("service")
            delay_ms = input_data.get("delay_ms", 500)
            try:
                # result = chaos_injector.add_delay(service, delay_ms)
                return {
                    "status": "success",
                    "service": service,
                    "injected_delay": f"{delay_ms}ms",
                    "duration": "5m",
                    "impact": "Simulating high load"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'terminate_instance', 'inject_latency'."
            }
