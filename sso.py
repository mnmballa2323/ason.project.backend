"""
SSO Integration — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Self-hosted Keycloak (Apache-2.0) for SAML 2.0 + OIDC authentication.
"""

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx


# ============================================================================
#  KEYCLOAK SSO CONFIGURATION
# ============================================================================

class SSOConfig:
    """Self-hosted Keycloak SSO configuration. NO external IdPs."""

    # Keycloak server (internal only — no public internet)
    KEYCLOAK_URL: str = os.getenv("KEYCLOAK_URL", "https://keycloak.libertycenter.one")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "ason-verification")
    CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "ason-orchestrator")
    CLIENT_SECRET: str = os.getenv("KEYCLOAK_CLIENT_SECRET", "")

    # Endpoints (auto-derived from Keycloak URL)
    @property
    def OIDC_DISCOVERY(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/.well-known/openid-configuration"

    @property
    def TOKEN_ENDPOINT(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/token"

    @property
    def AUTH_ENDPOINT(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/auth"

    @property
    def USERINFO_ENDPOINT(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/userinfo"

    @property
    def LOGOUT_ENDPOINT(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/logout"

    @property
    def JWKS_URI(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/openid-connect/certs"

    @property
    def SAML_METADATA(self) -> str:
        return f"{self.KEYCLOAK_URL}/realms/{self.KEYCLOAK_REALM}/protocol/saml/descriptor"


sso_config = SSOConfig()


# ============================================================================
#  OIDC TOKEN VALIDATION
# ============================================================================

class OIDCValidator:
    """
    Validates OIDC tokens from self-hosted Keycloak.
    Caches JWKS keys to avoid per-request network calls.
    """

    def __init__(self, config: SSOConfig = None):
        self.config = config or sso_config
        self._jwks_cache: Dict = {}
        self._jwks_cache_time: float = 0
        self._cache_ttl: int = 3600  # 1 hour

    async def _fetch_jwks(self) -> Dict:
        """Fetch JWKS (JSON Web Key Set) from Keycloak."""
        now = time.time()
        if self._jwks_cache and (now - self._jwks_cache_time) < self._cache_ttl:
            return self._jwks_cache

        try:
            async with httpx.AsyncClient(verify=True, timeout=10) as client:
                resp = await client.get(self.config.JWKS_URI)
                if resp.status_code == 200:
                    self._jwks_cache = resp.json()
                    self._jwks_cache_time = now
        except Exception:
            pass  # Use cached keys if Keycloak is temporarily unavailable
        return self._jwks_cache

    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Validate a JWT access token.
        Returns decoded claims if valid, None if invalid.

        In production, use python-jose or PyJWT with JWKS verification.
        This implementation provides the integration scaffolding.
        """
        if not token:
            return None

        # Strip "Bearer " prefix
        if token.startswith("Bearer "):
            token = token[7:]

        # Decode without verification for claim extraction
        # (In production, verify signature against JWKS)
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            # Base64 decode payload
            import base64
            payload = parts[1]
            # Add padding
            payload += "=" * (4 - len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))

            # Validate required claims
            now = time.time()
            if decoded.get("exp", 0) < now:
                return None  # Token expired
            if decoded.get("iss") != f"{self.config.KEYCLOAK_URL}/realms/{self.config.KEYCLOAK_REALM}":
                return None  # Wrong issuer

            return {
                "user_id": decoded.get("sub"),
                "email": decoded.get("email"),
                "name": decoded.get("name", decoded.get("preferred_username")),
                "tenant_id": decoded.get("tenant_id", decoded.get("azp")),
                "roles": decoded.get("realm_access", {}).get("roles", []),
                "groups": decoded.get("groups", []),
                "exp": decoded.get("exp"),
                "iat": decoded.get("iat"),
                "sso_provider": "keycloak",
            }
        except Exception:
            return None

    async def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict]:
        """Exchange authorization code for tokens (OIDC Authorization Code flow)."""
        try:
            async with httpx.AsyncClient(verify=True, timeout=10) as client:
                resp = await client.post(
                    self.config.TOKEN_ENDPOINT,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": self.config.CLIENT_ID,
                        "client_secret": self.config.CLIENT_SECRET,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass
        return None


# ============================================================================
#  KEYCLOAK REALM CONFIGURATION (for deployment)
# ============================================================================

KEYCLOAK_REALM_CONFIG = {
    "realm": "ason-verification",
    "enabled": True,
    "sslRequired": "all",
    "registrationAllowed": False,
    "loginWithEmailAllowed": True,
    "duplicateEmailsAllowed": False,
    "bruteForceProtected": True,
    "permanentLockout": False,
    "maxFailureWaitSeconds": 900,
    "failureFactor": 5,
    "passwordPolicy": "length(12) and upperCase(1) and lowerCase(1) and digits(1) and specialChars(1)",
    "otpPolicyType": "totp",
    "otpPolicyAlgorithm": "HmacSHA256",
    "accessTokenLifespan": 300,       # 5 minutes
    "ssoSessionIdleTimeout": 1800,    # 30 minutes
    "ssoSessionMaxLifespan": 36000,   # 10 hours
    "offlineSessionIdleTimeout": 2592000,  # 30 days

    "clients": [
        {
            "clientId": "ason-orchestrator",
            "protocol": "openid-connect",
            "publicClient": False,
            "directAccessGrantsEnabled": False,
            "standardFlowEnabled": True,
            "serviceAccountsEnabled": True,
            "redirectUris": [
                "https://qwen.libertycenter.one/*",
                "http://localhost:3001/*",
                "http://localhost:5173/*",
            ],
            "webOrigins": [
                "https://qwen.libertycenter.one",
                "http://localhost:3001",
                "http://localhost:5173",
            ],
            "defaultClientScopes": ["openid", "email", "profile", "roles"],
            "protocolMappers": [
                {
                    "name": "tenant_id",
                    "protocol": "openid-connect",
                    "protocolMapper": "oidc-usermodel-attribute-mapper",
                    "config": {
                        "user.attribute": "tenant_id",
                        "claim.name": "tenant_id",
                        "access.token.claim": "true",
                        "id.token.claim": "true",
                    },
                },
            ],
        },
        {
            "clientId": "ason-saml-sp",
            "protocol": "saml",
            "frontchannelLogout": True,
            "attributes": {
                "saml_name_id_format": "email",
                "saml.authnstatement": "true",
                "saml.server.signature": "true",
                "saml.signature.algorithm": "RSA_SHA256",
                "saml.encrypt": "true",
            },
        },
    ],

    "roles": {
        "realm": [
            {"name": "super_admin", "description": "Full platform access"},
            {"name": "tenant_admin", "description": "Tenant-level admin"},
            {"name": "engineer", "description": "Submit and manage verifications"},
            {"name": "auditor", "description": "Read-only audit access"},
            {"name": "viewer", "description": "Dashboard read-only"},
            {"name": "api_service", "description": "Machine-to-machine API"},
        ],
    },

    "groups": [
        {"name": "platform-admins", "realmRoles": ["super_admin"]},
        {"name": "tenant-admins", "realmRoles": ["tenant_admin"]},
        {"name": "engineers", "realmRoles": ["engineer"]},
        {"name": "auditors", "realmRoles": ["auditor"]},
        {"name": "viewers", "realmRoles": ["viewer"]},
    ],
}


# Global validator
oidc_validator = OIDCValidator()
