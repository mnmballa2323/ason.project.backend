from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..auth import require_role
from ..services.service_catalog import catalog_service
from ..services.task_manager import task_service
from ..services.chat_engine import chat_service

router = APIRouter()

class ServiceRequest(BaseModel):
    service_id: str
    payload: dict

class ChatRequest(BaseModel):
    message: str

@router.get("/catalog", dependencies=[Depends(require_role("Employee"))])
async def get_service_catalog():
    return {"services": await catalog_service.get_catalog()}

@router.post("/request", dependencies=[Depends(require_role("Employee"))])
async def submit_request(req: ServiceRequest, user: dict = Depends(require_role("Employee"))):
    service = await catalog_service.get_service(req.service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
        
    task = await task_service.create_task(user["username"], req.service_id, req.payload)
    return {"status": "submitted", "task_id": task["task_id"]}

@router.get("/tasks", dependencies=[Depends(require_role("Employee"))])
async def get_my_tasks(user: dict = Depends(require_role("Employee"))):
    return {"tasks": await task_service.get_user_tasks(user["username"])}

@router.post("/chat", dependencies=[Depends(require_role("Employee"))])
async def chat_interaction(req: ChatRequest, user: dict = Depends(require_role("Employee"))):
    return await chat_service.process_message(user["username"], req.message)
