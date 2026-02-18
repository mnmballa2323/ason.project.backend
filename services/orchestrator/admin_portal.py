"""
Admin Portal API — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Self-service tenant management, user provisioning, and usage analytics.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.admin")


# ============================================================================
#  ADMIN PORTAL SERVICE
# ============================================================================

class AdminPortal:
    """
    Provides administrative operations for:
    - Tenant lifecycle management
    - User provisioning and role assignment
    - Usage analytics and billing reports
    - System configuration and health
    """

    def __init__(self):
        self._audit_actions: list = []

    def _log_action(self, actor: str, action: str, target: str, details: dict = None):
        """Record admin action for audit trail."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "target": target,
            "details": details or {},
        }
        self._audit_actions.append(entry)
        logger.info(f"ADMIN: {actor} -> {action} on {target}")

    # --- Tenant Management ---

    def create_tenant(
        self, actor: str, name: str, slug: str, plan: str,
        admin_email: str, data_region: str = "LC1-East",
    ) -> dict:
        """Create a new tenant with initial admin user."""
        from tenancy import tenant_manager
        from licensing import license_manager
        import uuid

        tenant = tenant_manager.create_tenant(
            name=name, slug=slug, plan=plan, data_region=data_region,
        )

        license_key = license_manager.generate_license(
            tenant_id=tenant.tenant_id,
            tier=plan,
            validity_days=365,
        )

        admin_user = {
            "user_id": str(uuid.uuid4()),
            "email": admin_email,
            "tenant_id": tenant.tenant_id,
            "roles": ["tenant_admin"],
            "provisioned_by": actor,
        }

        self._log_action(actor, "create_tenant", tenant.tenant_id, {
            "name": name, "slug": slug, "plan": plan,
            "admin_email": admin_email, "data_region": data_region,
        })

        return {
            "tenant": tenant.to_dict(),
            "license_key": license_key,
            "admin_user": admin_user,
            "setup_url": f"https://{slug}.qwen.libertycenter.one/setup",
        }

    def list_tenants(self, actor: str) -> List[dict]:
        from tenancy import tenant_manager
        self._log_action(actor, "list_tenants", "all")
        return tenant_manager.list_tenants(active_only=False)

    def suspend_tenant(self, actor: str, tenant_id: str, reason: str) -> dict:
        from tenancy import tenant_manager
        tenant_manager.deactivate_tenant(tenant_id)
        self._log_action(actor, "suspend_tenant", tenant_id, {"reason": reason})
        return {"status": "suspended", "tenant_id": tenant_id, "reason": reason}

    # --- User Provisioning ---

    def provision_user(
        self, actor: str, tenant_id: str, email: str,
        display_name: str, roles: List[str],
    ) -> dict:
        """Provision a new user within a tenant."""
        import uuid
        user = {
            "user_id": str(uuid.uuid4()),
            "email": email,
            "display_name": display_name,
            "tenant_id": tenant_id,
            "roles": roles,
            "provisioned_at": datetime.now(timezone.utc).isoformat(),
            "provisioned_by": actor,
            "sso_linked": False,
        }
        self._log_action(actor, "provision_user", email, {
            "tenant_id": tenant_id, "roles": roles,
        })
        return user

    def update_user_roles(
        self, actor: str, tenant_id: str, user_id: str, roles: List[str],
    ) -> dict:
        self._log_action(actor, "update_roles", user_id, {
            "tenant_id": tenant_id, "new_roles": roles,
        })
        return {"user_id": user_id, "roles": roles, "updated_by": actor}

    def deactivate_user(self, actor: str, tenant_id: str, user_id: str) -> dict:
        self._log_action(actor, "deactivate_user", user_id, {"tenant_id": tenant_id})
        return {"user_id": user_id, "status": "deactivated"}

    # --- Usage Analytics ---

    def get_usage_analytics(self, tenant_id: str) -> dict:
        """Get comprehensive usage analytics for a tenant."""
        from licensing import license_manager
        from sla import sla_dashboard

        license_info = license_manager.get_active_license(tenant_id)
        quota = license_manager.check_quota(tenant_id)
        usage_report = license_manager.get_usage_report(tenant_id, days=30)

        slo_status = sla_dashboard.get_slo_status(
            tenant_id, tier=license_info.tier if license_info else "enterprise"
        )

        return {
            "tenant_id": tenant_id,
            "license": license_info.to_dict() if license_info else None,
            "quota": quota,
            "usage_30d": usage_report,
            "slo_status": slo_status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_platform_analytics(self) -> dict:
        """Get platform-wide analytics for super admins."""
        from tenancy import tenant_manager
        from sla import sla_dashboard

        tenants = tenant_manager.list_tenants(active_only=False)
        dashboard = sla_dashboard.get_dashboard_summary()

        return {
            "total_tenants": len(tenants),
            "active_tenants": sum(1 for t in tenants if t.get("is_active")),
            "plans": self._count_by_key(tenants, "plan"),
            "regions": self._count_by_key(tenants, "data_region"),
            "platform_health": dashboard,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # --- Admin Audit Log ---

    def get_admin_audit_log(self, limit: int = 100) -> List[dict]:
        return self._audit_actions[-limit:]

    # --- Helpers ---

    @staticmethod
    def _count_by_key(items: List[dict], key: str) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in items:
            val = item.get(key, "unknown")
            counts[val] = counts.get(val, 0) + 1
        return counts


# Global singleton
admin_portal = AdminPortal()
