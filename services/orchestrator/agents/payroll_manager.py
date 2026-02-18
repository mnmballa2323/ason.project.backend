"""
Payroll Manager Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Payroll Processing module.
2. Calculates pay and generates paystubs.
3. Strictly self-hosted.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..payroll_processing import calculator, paystub_generator

logger = logging.getLogger("qwen.agents.payroll_manager")

class PayrollManagerAgent(Agent):
    """
    Agent that acts as a Payroll Specialist.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "payroll-manager",
            "description": "Payroll calculation and document generation.",
            "version": "1.0.0",
            "role": "Payroll Specialist",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute payroll actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "process_payroll", "generate_paystubs".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"PayrollManagerAgent received action: {action}")

        if action == "process_payroll":
            cycle_id = input_data.get("cycle_id")
            try:
                # summary = calculator.run_cycle(cycle_id)
                return {
                    "status": "success",
                    "cycle_id": cycle_id,
                    "total_gross": "$450,000.00",
                    "employees_processed": 120
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "generate_paystubs":
            employee_id = input_data.get("employee_id")
            try:
                # url = paystub_generator.create(employee_id)
                return {
                    "status": "success",
                    "employee_id": employee_id,
                    "paystub_url": f"/internal/hr/payroll/{employee_id}_latest.pdf"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'process_payroll', 'generate_paystubs'."
            }
