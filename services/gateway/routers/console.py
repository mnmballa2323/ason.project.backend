from fastapi import APIRouter, Depends
from ..auth import require_role
from ..services.system_monitor import monitor_service
from ..services.control_plane import control_plane_service
from ..services.audit_log import audit_service

router = APIRouter()

@router.get("/status", dependencies=[Depends(require_role("Admin"))])
async def get_system_status():
    """
    Returns internal system health. Zero external calls.
    """
    return await monitor_service.get_system_status()

@router.post("/control/agent", dependencies=[Depends(require_role("Admin"))])
async def control_agent(action: str, agent_id: str, user: dict = Depends(require_role("Admin"))):
    requester = user["username"]
    await audit_service.log_event(requester, action.upper(), agent_id, "ATTEMPT")
    
    if action == "restart":
        result = await control_plane_service.restart_agent(agent_id, requester)
        await audit_service.log_event(requester, "RESTART", agent_id, "SUCCESS")
        return result
    elif action == "kill":
        result = await control_plane_service.emergency_stop(agent_id, requester)
        await audit_service.log_event(requester, "KILL", agent_id, "SUCCESS")
        return result
        
    return {"status": "error", "message": "Invalid action"}

@router.get("/audit/logs", dependencies=[Depends(require_role("Admin"))])
async def get_audit_logs():
    return await audit_service.view_recent_logs()
