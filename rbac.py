"""
Role-Based Access Control (RBAC) — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Provides role hierarchy, permission matrix, and tenant-scoped authorization.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set


# ============================================================================
#  ROLES & PERMISSIONS
# ============================================================================

class Role(str, Enum):
    SUPER_ADMIN = "super_admin"    # Platform-level admin (multi-tenant)
    TENANT_ADMIN = "tenant_admin"  # Tenant-level admin
    ENGINEER = "engineer"          # Can submit and manage verification jobs
    AUDITOR = "auditor"            # Read-only: audit logs, reports, exports
    VIEWER = "viewer"              # Read-only: dashboard, job status
    API_SERVICE = "api_service"    # Machine-to-machine API access


class Permission(str, Enum):
    # --- Verification ---
    VERIFY_SUBMIT = "verify:submit"
    VERIFY_BATCH = "verify:batch"
    VERIFY_STATUS = "verify:status"
    VERIFY_CANCEL = "verify:cancel"

    # --- Audit ---
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"
    AUDIT_VERIFY_CHAIN = "audit:verify_chain"

    # --- Admin ---
    ADMIN_USERS = "admin:users"
    ADMIN_TENANTS = "admin:tenants"
    ADMIN_ROLES = "admin:roles"
    ADMIN_CONFIG = "admin:config"

    # --- System ---
    SYSTEM_HEALTH = "system:health"
    SYSTEM_METRICS = "system:metrics"
    SYSTEM_PLUGINS = "system:plugins"
    SYSTEM_MODEL_REGISTRY = "system:model_registry"
    SYSTEM_WEBHOOKS = "system:webhooks"
    SYSTEM_UPGRADE = "system:upgrade"

    # --- Data ---
    DATA_EXPORT = "data:export"
    DATA_DELETE = "data:delete"
    DATA_RESIDENCY = "data:residency"


# Role → Permission mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),  # All permissions

    Role.TENANT_ADMIN: {
        Permission.VERIFY_SUBMIT, Permission.VERIFY_BATCH,
        Permission.VERIFY_STATUS, Permission.VERIFY_CANCEL,
        Permission.AUDIT_VIEW, Permission.AUDIT_EXPORT,
        Permission.AUDIT_VERIFY_CHAIN,
        Permission.ADMIN_USERS, Permission.ADMIN_ROLES,
        Permission.ADMIN_CONFIG,
        Permission.SYSTEM_HEALTH, Permission.SYSTEM_METRICS,
        Permission.SYSTEM_WEBHOOKS,
        Permission.DATA_EXPORT,
    },

    Role.ENGINEER: {
        Permission.VERIFY_SUBMIT, Permission.VERIFY_BATCH,
        Permission.VERIFY_STATUS, Permission.VERIFY_CANCEL,
        Permission.AUDIT_VIEW,
        Permission.SYSTEM_HEALTH, Permission.SYSTEM_METRICS,
        Permission.SYSTEM_MODEL_REGISTRY,
    },

    Role.AUDITOR: {
        Permission.VERIFY_STATUS,
        Permission.AUDIT_VIEW, Permission.AUDIT_EXPORT,
        Permission.AUDIT_VERIFY_CHAIN,
        Permission.SYSTEM_HEALTH,
        Permission.DATA_EXPORT,
    },

    Role.VIEWER: {
        Permission.VERIFY_STATUS,
        Permission.AUDIT_VIEW,
        Permission.SYSTEM_HEALTH,
    },

    Role.API_SERVICE: {
        Permission.VERIFY_SUBMIT, Permission.VERIFY_BATCH,
        Permission.VERIFY_STATUS,
        Permission.SYSTEM_HEALTH,
        Permission.SYSTEM_MODEL_REGISTRY,
    },
}


# ============================================================================
#  USER MODEL
# ============================================================================

class User:
    """Represents an authenticated user with tenant-scoped roles."""

    def __init__(
        self,
        user_id: str,
        email: str,
        display_name: str,
        tenant_id: str,
        roles: List[Role],
        is_active: bool = True,
        sso_provider: str = None,
        mfa_enabled: bool = False,
    ):
        self.user_id = user_id
        self.email = email
        self.display_name = display_name
        self.tenant_id = tenant_id
        self.roles = roles
        self.is_active = is_active
        self.sso_provider = sso_provider
        self.mfa_enabled = mfa_enabled
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_login = None

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission through any assigned role."""
        for role in self.roles:
            if permission in ROLE_PERMISSIONS.get(role, set()):
                return True
        return False

    def has_role(self, role: Role) -> bool:
        return role in self.roles

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "display_name": self.display_name,
            "tenant_id": self.tenant_id,
            "roles": [r.value for r in self.roles],
            "is_active": self.is_active,
            "sso_provider": self.sso_provider,
            "mfa_enabled": self.mfa_enabled,
            "created_at": self.created_at,
            "last_login": self.last_login,
        }


# ============================================================================
#  AUTHORIZATION MIDDLEWARE
# ============================================================================

class AuthorizationError(Exception):
    """Raised when user lacks required permission."""
    def __init__(self, user_id: str, permission: str, tenant_id: str = ""):
        self.user_id = user_id
        self.permission = permission
        self.tenant_id = tenant_id
        super().__init__(f"User {user_id} lacks permission {permission} in tenant {tenant_id}")


def require_permission(permission: Permission):
    """Decorator to enforce permission checks on endpoint handlers.

    Usage:
        @app.post("/verify/run")
        @require_permission(Permission.VERIFY_SUBMIT)
        async def submit_verification(request: Request, user: User):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user")
            if not user:
                raise AuthorizationError("unknown", permission.value)
            if not user.has_permission(permission):
                raise AuthorizationError(user.user_id, permission.value, user.tenant_id)
            return await func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


def require_role(role: Role):
    """Decorator to enforce role checks."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user = kwargs.get("user")
            if not user or not user.has_role(role):
                raise AuthorizationError(
                    user.user_id if user else "unknown",
                    f"role:{role.value}",
                    user.tenant_id if user else ""
                )
            return await func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    return decorator


# ============================================================================
#  PERMISSION MATRIX EXPORT (for Admin UI)
# ============================================================================

def get_permission_matrix() -> Dict[str, Dict[str, bool]]:
    """Export the full role/permission matrix for the admin portal."""
    matrix = {}
    for role in Role:
        role_perms = ROLE_PERMISSIONS.get(role, set())
        matrix[role.value] = {
            perm.value: perm in role_perms
            for perm in Permission
        }
    return matrix


def get_roles_summary() -> List[dict]:
    """Export role descriptions for documentation."""
    descriptions = {
        Role.SUPER_ADMIN: "Platform-level administrator with full access to all tenants and features",
        Role.TENANT_ADMIN: "Tenant-level administrator with full access within their tenant",
        Role.ENGINEER: "Can submit, manage, and cancel verification jobs",
        Role.AUDITOR: "Read-only access to audit logs, reports, and data exports",
        Role.VIEWER: "Read-only access to dashboards and job status",
        Role.API_SERVICE: "Machine-to-machine API access for CI/CD integration",
    }
    return [
        {
            "role": role.value,
            "description": descriptions[role],
            "permission_count": len(ROLE_PERMISSIONS.get(role, set())),
            "permissions": sorted(p.value for p in ROLE_PERMISSIONS.get(role, set())),
        }
        for role in Role
    ]
