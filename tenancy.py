"""
Multi-Tenancy System — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Provides tenant isolation, per-tenant config, data partitioning.
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class Tenant:
    """Represents an isolated tenant with its own config and data boundaries."""

    def __init__(
        self,
        tenant_id: str,
        name: str,
        slug: str,
        plan: str = "enterprise",
        config: Dict[str, Any] = None,
        branding: Dict[str, str] = None,
        data_region: str = "LC1-East",
        max_users: int = 50,
        max_claims_per_day: int = 10000,
        features: List[str] = None,
    ):
        self.tenant_id = tenant_id
        self.name = name
        self.slug = slug
        self.plan = plan
        self.config = config or {}
        self.branding = branding or {}
        self.data_region = data_region
        self.max_users = max_users
        self.max_claims_per_day = max_claims_per_day
        self.features = features or ["verification", "audit", "export"]
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.is_active = True

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "slug": self.slug,
            "plan": self.plan,
            "data_region": self.data_region,
            "max_users": self.max_users,
            "max_claims_per_day": self.max_claims_per_day,
            "features": self.features,
            "branding": self.branding,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class TenantManager:
    """
    Manages multi-tenant lifecycle.
    In-memory with optional PostgreSQL persistence.

    Data Isolation Strategy:
    - Row-level security: All queries filtered by tenant_id
    - Separate schemas: Optional per-tenant PostgreSQL schema
    - Object storage: Prefixed by tenant_id (e.g., s3://bucket/{tenant_id}/...)
    - Audit chain: Per-tenant audit logs with cross-tenant integrity
    """

    # Default plans with feature/limit matrices
    PLANS = {
        "starter": {
            "max_users": 5,
            "max_claims_per_day": 500,
            "features": ["verification", "audit"],
            "support": "community",
            "sla": "99.0%",
        },
        "professional": {
            "max_users": 25,
            "max_claims_per_day": 5000,
            "features": ["verification", "audit", "export", "webhooks", "batch"],
            "support": "business-hours",
            "sla": "99.9%",
        },
        "enterprise": {
            "max_users": 100,
            "max_claims_per_day": 50000,
            "features": ["verification", "audit", "export", "webhooks", "batch",
                         "sso", "rbac", "white-label", "siem", "data-residency"],
            "support": "24x7",
            "sla": "99.99%",
        },
        "government": {
            "max_users": 200,
            "max_claims_per_day": 100000,
            "features": ["verification", "audit", "export", "webhooks", "batch",
                         "sso", "rbac", "white-label", "siem", "data-residency",
                         "air-gap", "fips-140-3", "fedramp"],
            "support": "24x7-dedicated",
            "sla": "99.999%",
        },
    }

    def __init__(self):
        self._tenants: Dict[str, Tenant] = {}
        self._db_available = False

    async def initialize(self):
        """Initialize tenant store. Try PostgreSQL, fall back to in-memory."""
        db_url = os.getenv("POSTGRES_URL", "")
        if db_url:
            try:
                import psycopg
                async with await psycopg.AsyncConnection.connect(db_url) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("""
                            CREATE TABLE IF NOT EXISTS tenants (
                                tenant_id TEXT PRIMARY KEY,
                                name TEXT NOT NULL,
                                slug TEXT UNIQUE NOT NULL,
                                plan TEXT DEFAULT 'enterprise',
                                config JSONB DEFAULT '{}',
                                branding JSONB DEFAULT '{}',
                                data_region TEXT DEFAULT 'LC1-East',
                                max_users INTEGER DEFAULT 50,
                                max_claims_per_day INTEGER DEFAULT 10000,
                                features JSONB DEFAULT '[]',
                                is_active BOOLEAN DEFAULT TRUE,
                                created_at TIMESTAMPTZ DEFAULT NOW()
                            );
                            CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
                        """)
                    await conn.commit()
                self._db_available = True
            except Exception:
                pass

    def create_tenant(
        self,
        name: str,
        slug: str,
        plan: str = "enterprise",
        data_region: str = "LC1-East",
        branding: Dict[str, str] = None,
    ) -> Tenant:
        """Create a new tenant with plan-based defaults."""
        if slug in {t.slug for t in self._tenants.values()}:
            raise ValueError(f"Tenant slug '{slug}' already exists")

        if plan not in self.PLANS:
            raise ValueError(f"Invalid plan: {plan}. Must be one of: {list(self.PLANS.keys())}")

        plan_config = self.PLANS[plan]
        tenant = Tenant(
            tenant_id=str(uuid.uuid4()),
            name=name,
            slug=slug,
            plan=plan,
            data_region=data_region,
            max_users=plan_config["max_users"],
            max_claims_per_day=plan_config["max_claims_per_day"],
            features=plan_config["features"],
            branding=branding or {},
        )
        self._tenants[tenant.tenant_id] = tenant
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def get_by_slug(self, slug: str) -> Optional[Tenant]:
        return next((t for t in self._tenants.values() if t.slug == slug), None)

    def list_tenants(self, active_only: bool = True) -> List[dict]:
        tenants = self._tenants.values()
        if active_only:
            tenants = [t for t in tenants if t.is_active]
        return [t.to_dict() for t in tenants]

    def deactivate_tenant(self, tenant_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.is_active = False
            return True
        return False

    def has_feature(self, tenant_id: str, feature: str) -> bool:
        """Check if tenant's plan includes a specific feature."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        return feature in tenant.features

    def check_daily_quota(self, tenant_id: str, current_count: int) -> bool:
        """Check if tenant is within daily claim quota."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        return current_count < tenant.max_claims_per_day

    def get_tenant_db_schema(self, tenant_id: str) -> str:
        """Get the PostgreSQL schema name for tenant data isolation."""
        return f"tenant_{tenant_id.replace('-', '_')}"


# Global singleton
tenant_manager = TenantManager()
