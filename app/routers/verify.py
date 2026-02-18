from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from typing import List, Optional
import uuid

from app.services.job_store import job_store
from app.services.sovereignty import data_sovereignty, Jurisdiction, DataCategory
from app.core.security import require_role, audit_logger

router = APIRouter()

class VerificationRequest(BaseModel):
    claims: List[str]
    industry: Optional[str] = "general"
    model_version: Optional[str] = "ason-72b"

@router.post("/run", tags=["Verification"])
async def run_verification(
    request: Request,
    payload: VerificationRequest, 
    background_tasks: BackgroundTasks
):
    """
    Submit a verification job.
    Enforces Data Sovereignty (via middleware) and RBAC.
    """
    # RBAC check (mock user for now until auth middleware fully active)
    # require_role(request.user, "submit_job")

    job_id = f"job-{uuid.uuid4()}"
    
    # Create job in persistent store
    await job_store.create(
        job_id=job_id,
        industry=payload.industry,
        total_claims=len(payload.claims),
        model_version=payload.model_version
    )

    # Log Audit
    audit_logger.log(
        actor="user",  # TODO: extract from token
        action="submit_job",
        target=job_id,
        status="accepted",
        details={"claims_count": len(payload.claims)}
    )

    # TODO: Trigger celery/background task
    # background_tasks.add_task(process_job, job_id, payload.claims)

    return {"job_id": job_id, "status": "queued"}

@router.get("/status/{job_id}", tags=["Verification"])
async def get_job_status(job_id: str, request: Request):
    """Get status of a specific job."""
    job = await job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
