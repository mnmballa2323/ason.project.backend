"""
Webhook & Event System — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Outbound webhooks for job completion, event bus for integrations.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger("qwen.webhooks")


# ============================================================================
#  EVENT TYPES
# ============================================================================

class EventType(str, Enum):
    # Verification events
    JOB_SUBMITTED = "verification.job.submitted"
    JOB_COMPLETED = "verification.job.completed"
    JOB_FAILED = "verification.job.failed"
    JOB_CANCELLED = "verification.job.cancelled"

    # Batch events
    BATCH_STARTED = "verification.batch.started"
    BATCH_COMPLETED = "verification.batch.completed"

    # Audit events
    AUDIT_CHAIN_VERIFIED = "audit.chain.verified"
    AUDIT_CHAIN_BROKEN = "audit.chain.broken"
    AUDIT_EXPORT_COMPLETED = "audit.export.completed"

    # System events
    SYSTEM_HEALTH_DEGRADED = "system.health.degraded"
    SYSTEM_HEALTH_RESTORED = "system.health.restored"
    MODEL_REGISTRY_UPDATED = "system.model.updated"

    # Tenant events
    TENANT_QUOTA_WARNING = "tenant.quota.warning"  # 80% usage
    TENANT_QUOTA_EXCEEDED = "tenant.quota.exceeded"
    LICENSE_EXPIRING_SOON = "tenant.license.expiring"

    # Security events
    SECURITY_ANOMALY = "security.anomaly.detected"
    LOGIN_FAILED_THRESHOLD = "security.login.failed"


# ============================================================================
#  WEBHOOK SUBSCRIPTION
# ============================================================================

class WebhookSubscription:
    """A registered webhook endpoint."""

    def __init__(
        self,
        webhook_id: str,
        tenant_id: str,
        url: str,
        events: List[EventType],
        secret: str = "",
        is_active: bool = True,
        description: str = "",
        headers: Dict[str, str] = None,
        retry_count: int = 3,
        timeout_seconds: int = 10,
    ):
        self.webhook_id = webhook_id
        self.tenant_id = tenant_id
        self.url = url
        self.events = events
        self.secret = secret or hashlib.sha256(os.urandom(32)).hexdigest()
        self.is_active = is_active
        self.description = description
        self.headers = headers or {}
        self.retry_count = retry_count
        self.timeout_seconds = timeout_seconds
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_triggered = None
        self.failure_count = 0
        self.success_count = 0

    def to_dict(self) -> dict:
        return {
            "webhook_id": self.webhook_id,
            "tenant_id": self.tenant_id,
            "url": self.url,
            "events": [e.value for e in self.events],
            "is_active": self.is_active,
            "description": self.description,
            "retry_count": self.retry_count,
            "created_at": self.created_at,
            "last_triggered": self.last_triggered,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
        }


# ============================================================================
#  EVENT BUS
# ============================================================================

class Event:
    """An event to be dispatched to subscribers."""

    def __init__(
        self, event_type: EventType, tenant_id: str,
        payload: Dict[str, Any], source: str = "orchestrator",
    ):
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.tenant_id = tenant_id
        self.payload = payload
        self.source = source
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "tenant_id": self.tenant_id,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp,
        }


class WebhookManager:
    """
    Manages webhook subscriptions and event delivery.
    Supports HMAC-SHA256 signed payloads for verification.
    """

    def __init__(self):
        self._subscriptions: Dict[str, WebhookSubscription] = {}
        self._event_log: List[Dict] = []
        self._internal_handlers: Dict[EventType, List[Callable]] = {}
        self._delivery_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """Start the delivery worker."""
        self._http_client = httpx.AsyncClient(
            timeout=30,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
        )
        asyncio.create_task(self._delivery_worker())

    # --- Subscription Management ---

    def register(
        self, tenant_id: str, url: str, events: List[EventType],
        description: str = "", headers: Dict[str, str] = None,
    ) -> WebhookSubscription:
        """Register a new webhook subscription."""
        sub = WebhookSubscription(
            webhook_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            url=url,
            events=events,
            description=description,
            headers=headers,
        )
        self._subscriptions[sub.webhook_id] = sub
        logger.info(f"Registered webhook {sub.webhook_id} for tenant {tenant_id}")
        return sub

    def unregister(self, webhook_id: str) -> bool:
        if webhook_id in self._subscriptions:
            del self._subscriptions[webhook_id]
            return True
        return False

    def list_subscriptions(self, tenant_id: str) -> List[dict]:
        return [
            s.to_dict() for s in self._subscriptions.values()
            if s.tenant_id == tenant_id
        ]

    # --- Internal Handler Registration ---

    def on(self, event_type: EventType, handler: Callable):
        """Register an internal async handler for an event type."""
        if event_type not in self._internal_handlers:
            self._internal_handlers[event_type] = []
        self._internal_handlers[event_type].append(handler)

    # --- Event Emission ---

    async def emit(self, event: Event):
        """Emit an event to all matching subscribers and internal handlers."""
        event_dict = event.to_dict()
        self._event_log.append(event_dict)

        # Trim log to 10K events
        if len(self._event_log) > 10000:
            self._event_log = self._event_log[-10000:]

        # Internal handlers (synchronous within process)
        handlers = self._internal_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Internal handler error: {e}")

        # Queue webhook deliveries
        for sub in self._subscriptions.values():
            if (sub.is_active
                    and sub.tenant_id == event.tenant_id
                    and event.event_type in sub.events):
                await self._delivery_queue.put((sub, event_dict))

    # --- Webhook Delivery ---

    async def _delivery_worker(self):
        """Background worker that delivers webhooks with retries."""
        while True:
            try:
                sub, event_dict = await self._delivery_queue.get()
                await self._deliver(sub, event_dict)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Delivery worker error: {e}")

    async def _deliver(self, sub: WebhookSubscription, event_dict: Dict):
        """Deliver a webhook with HMAC signature and retries."""
        payload_json = json.dumps(event_dict, sort_keys=True)
        signature = hmac.new(
            sub.secret.encode(), payload_json.encode(), hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Ason-Signature": f"sha256={signature}",
            "X-Ason-Event": event_dict.get("event_type", ""),
            "X-Ason-Delivery": event_dict.get("event_id", ""),
            "User-Agent": "Ason-Webhook/2.0",
            **sub.headers,
        }

        for attempt in range(sub.retry_count):
            try:
                resp = await self._http_client.post(
                    sub.url, content=payload_json, headers=headers,
                    timeout=sub.timeout_seconds,
                )
                if resp.status_code < 300:
                    sub.success_count += 1
                    sub.last_triggered = datetime.now(timezone.utc).isoformat()
                    logger.info(f"Webhook {sub.webhook_id} delivered: {resp.status_code}")
                    return

                logger.warning(f"Webhook {sub.webhook_id} returned {resp.status_code}, attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"Webhook {sub.webhook_id} network error: {e}, attempt {attempt + 1}")

            # Exponential backoff: 1s, 4s, 16s
            await asyncio.sleep(min(4 ** attempt, 60))

        # Mark as failed after all retries
        sub.failure_count += 1
        logger.error(f"Webhook {sub.webhook_id} delivery failed after {sub.retry_count} attempts")

        # Auto-disable after 10 consecutive failures
        if sub.failure_count >= 10:
            sub.is_active = False
            logger.warning(f"Webhook {sub.webhook_id} auto-disabled after 10 failures")

    def get_event_log(self, tenant_id: str, limit: int = 100) -> List[dict]:
        """Get recent events for a tenant."""
        tenant_events = [e for e in self._event_log if e["tenant_id"] == tenant_id]
        return tenant_events[-limit:]

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()


# Global singleton
webhook_manager = WebhookManager()
