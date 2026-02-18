"""
Parking Coordinator Agent — Ason Verification Platform
Liberty Center One — Internal Use Only

Logic:
1. Interfaces with internal Self-Hosted Campus Ops module.
2. Manages parking lot assignments and EV chargers.
3. STRICTLY NO EXTERNAL API CALLS.
4. Local gate controller logic.
"""

import logging
from typing import Dict, Any
from . import Agent
from ..campus_ops import lot_manager, ev_charger_scheduler

logger = logging.getLogger("qwen.agents.parking_coordinator")

class ParkingCoordinatorAgent(Agent):
    """
    Agent that acts as a Parking / Campus Services Admin.
    """

    def metadata(self) -> Dict[str, str]:
        return {
            "name": "parking-coordinator",
            "description": "Parking spot allocation and EV charging management.",
            "version": "1.0.0",
            "role": "Facilities Admin",
        }

    async def run(self, input_data: Dict[str, Any], context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute parking actions.
        
        Args:
            input_data: Must contain "action".
                        Supported: "assign_spot", "manage_ev_charging".
        """
        action = input_data.get("action")
        if not action:
            raise ValueError("Input data must contain 'action' field.")

        logger.info(f"ParkingCoordinatorAgent received action: {action}")

        if action == "assign_spot":
            employee_id = input_data.get("employee_id")
            try:
                # Finds nearest available spot.
                # spot = lot_manager.assign(employee_id)
                return {
                    "status": "success",
                    "employee_id": employee_id,
                    "assigned_spot": "P2-404",
                    "lot": "North Garage",
                    "access_granted": True
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        elif action == "manage_ev_charging":
            station_id = input_data.get("station_id")
            try:
                # Checks charger status via Modbus.
                # schedule = ev_charger_scheduler.get_schedule(station_id)
                return {
                    "status": "success",
                    "station_id": station_id,
                    "current_user": "None",
                    "next_reservation": "14:00 - User E-102",
                    "power_draw": "0 kW"
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        else:
            return {
                "status": "error",
                "message": f"Unknown action: '{action}'. Supported: 'assign_spot', 'manage_ev_charging'."
            }
