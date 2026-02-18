"""
Webhook Router — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Endpoints for internal webhooks (Alertmanager, GitOps).
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any
import logging

from services.self_healing import self_healing
from services.dr_manager import dr_manager

logger = logging.getLogger("qwen.webhooks")
router = APIRouter(tags=["Internal Webhooks"])

class Alert(BaseModel):
    status: str
    labels: Dict[str, Any]
    annotations: Dict[str, Any]
    startsAt: str

class AlertManagerPayload(BaseModel):
    version: str
    groupKey: str
    status: str
    receiver: str
    alerts: List[Alert]

@router.post("/internal/alert")
async def receive_alert(payload: AlertManagerPayload):
    """
    Receive critical alerts from Alertmanager.
    Triggers Self-Healing or DR Failover based on severity/label.
    """
    logger.info(f"Received {len(payload.alerts)} alerts from Alertmanager")
    
    for alert in payload.alerts:
        alert_name = alert.labels.get("alertname", "Unknown")
        severity = alert.labels.get("severity", "info")
        instance = alert.labels.get("instance", "unknown-instance")
        
        logger.warning(f"Processing Alert: {alert_name} ({severity}) on {instance}")
        
        # Logic: Dispatch to correct handler
        if alert_name == "RegionDown" and severity == "critical":
            # Critical Region Failure -> Trigger DR
            dr_manager.initiate_failover(reason=f"Alertmanager: {alert_name} on {instance}")
            
        elif severity == "critical":
            # Other critical component failures -> Self Healing
            # Mapping Alertmanager 'instance' to SelfHealing 'target'
            self_healing.trigger_remediation(target=instance, issue=alert_name)
            
    return {"status": "processed", "alerts_handled": len(payload.alerts)}
