"""
Task Manager Service
Tracks status of internal user requests IN-MEMORY.
STRICTLY INTERNAL USE ONLY.
"""

import uuid
import datetime
from typing import List, Dict, Any, Optional

class TaskManager:
    def __init__(self):
        # In-memory store: {task_id: task_dict}
        self._tasks = {}

    async def create_task(self, user: str, service_id: str, payload: dict) -> Dict[str, Any]:
        task_id = f"TASK-{str(uuid.uuid4())[:8].upper()}"
        timestamp = datetime.datetime.now().isoformat()
        
        task = {
            "task_id": task_id,
            "user": user,
            "service_id": service_id,
            "status": "PENDING",
            "created_at": timestamp,
            "updated_at": timestamp,
            "payload": payload,
            "result": None
        }
        
        self._tasks[task_id] = task
        
        # Simulate immediate processing for demo
        # In real system, this pushes to a queue
        await self._simulate_processing(task_id)
        
        return task

    async def _simulate_processing(self, task_id: str):
        # Mock async processing
        task = self._tasks[task_id]
        task["status"] = "COMPLETED"
        task["updated_at"] = datetime.datetime.now().isoformat()
        task["result"] = {"message": "Processed successfully by internal agent."}

    async def get_user_tasks(self, user: str) -> List[Dict[str, Any]]:
        return [t for t in self._tasks.values() if t["user"] == user]

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self._tasks.get(task_id)

# Singleton
task_service = TaskManager()
