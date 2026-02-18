from fastapi import APIRouter, Depends
from app.services.job_store import job_store
from app.core.security import audit_logger

router = APIRouter()

@router.get("/stats", tags=["Dashboard"])
async def get_dashboard_stats():
    """Aggregate stats for the executive dashboard."""
    jobs = await job_store.list_all()
    # Simple aggregation
    total = len(jobs)
    completed = sum(1 for j in jobs if j.get("status") == "completed")
    failed = sum(1 for j in jobs if j.get("status") == "failed")
    
    return {
        "total_jobs": total,
        "completed": completed,
        "failed": failed,
        "active": total - completed - failed
    }

@router.get("/audit/log", tags=["Dashboard"])
async def get_audit_log():
    """Access immutable audit trails."""
    # RBAC check would go here
    return audit_logger.export_logs()
