"""
License Key System — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Cryptographic license validation, feature gating, usage metering.
Supports both online and OFFLINE (air-gapped) validation.
"""

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ============================================================================
#  LICENSE KEY STRUCTURE
# ============================================================================

class LicenseKey:
    """
    Cryptographic license key with embedded claims.

    Format: ASON-{TIER}-{ENCODED_PAYLOAD}-{SIGNATURE}

    The payload contains:
    - tenant_id: Tenant this license belongs to
    - tier: starter | professional | enterprise | government
    - features: List of enabled feature codes
    - max_users: Maximum concurrent users
    - max_claims_per_day: Daily claim quota
    - issued_at: ISO timestamp
    - expires_at: ISO timestamp
    - license_id: Unique license ID
    - issuer: "Liberty Center One"

    Validation is done with HMAC-SHA256 using a shared secret.
    NO PHONE-HOME. NO EXTERNAL API CALLS. Fully offline-capable.
    """

    def __init__(self, payload: Dict[str, Any], signature: str = ""):
        self.payload = payload
        self.signature = signature

    @property
    def tenant_id(self) -> str:
        return self.payload.get("tenant_id", "")

    @property
    def tier(self) -> str:
        return self.payload.get("tier", "starter")

    @property
    def features(self) -> List[str]:
        return self.payload.get("features", [])

    @property
    def max_users(self) -> int:
        return self.payload.get("max_users", 5)

    @property
    def max_claims_per_day(self) -> int:
        return self.payload.get("max_claims_per_day", 500)

    @property
    def expires_at(self) -> str:
        return self.payload.get("expires_at", "")

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return True
        try:
            exp = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) > exp
        except Exception:
            return True

    def to_dict(self) -> dict:
        return {
            "license_id": self.payload.get("license_id"),
            "tenant_id": self.tenant_id,
            "tier": self.tier,
            "features": self.features,
            "max_users": self.max_users,
            "max_claims_per_day": self.max_claims_per_day,
            "issued_at": self.payload.get("issued_at"),
            "expires_at": self.expires_at,
            "is_expired": self.is_expired,
            "issuer": self.payload.get("issuer", "Liberty Center One"),
        }


# ============================================================================
#  LICENSE MANAGER
# ============================================================================

class LicenseManager:
    """
    Generates and validates license keys.
    Uses HMAC-SHA256 for tamper-proof signatures.
    100% offline — no network calls required.
    """

    def __init__(self, secret_key: str = None):
        self._secret = (secret_key or os.getenv(
            "ASON_LICENSE_SECRET",
            "ason-lc1-default-dev-secret-replace-in-production"
        )).encode()
        self._active_licenses: Dict[str, LicenseKey] = {}
        self._usage_meters: Dict[str, Dict[str, int]] = {}  # tenant_id -> {date: count}

    def _sign(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature."""
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

    def _verify_signature(self, payload: str, signature: str) -> bool:
        """Verify HMAC-SHA256 signature (constant-time comparison)."""
        expected = self._sign(payload)
        return hmac.compare_digest(expected, signature)

    def generate_license(
        self,
        tenant_id: str,
        tier: str = "enterprise",
        features: List[str] = None,
        max_users: int = 50,
        max_claims_per_day: int = 10000,
        validity_days: int = 365,
    ) -> str:
        """
        Generate a cryptographic license key string.

        Returns: ASON-{TIER}-{BASE64_PAYLOAD}-{HMAC_SIGNATURE}
        """
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        payload = {
            "license_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "tier": tier,
            "features": features or self._default_features(tier),
            "max_users": max_users,
            "max_claims_per_day": max_claims_per_day,
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=validity_days)).isoformat(),
            "issuer": "Liberty Center One",
            "version": "2.0",
        }

        payload_json = json.dumps(payload, sort_keys=True)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")
        signature = self._sign(payload_json)

        tier_code = tier[:3].upper()
        return f"ASON-{tier_code}-{payload_b64}-{signature[:32]}"

    def validate_license(self, license_key: str) -> Optional[LicenseKey]:
        """
        Validate a license key string.
        Returns LicenseKey if valid, None if invalid.
        100% OFFLINE — no network calls.
        """
        try:
            parts = license_key.split("-", 3)
            if len(parts) != 4 or parts[0] != "ASON":
                return None

            _, tier_code, payload_b64, sig_prefix = parts

            # Restore base64 padding
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload_json = base64.urlsafe_b64decode(payload_b64).decode()
            payload = json.loads(payload_json)

            # Verify signature
            full_sig = self._sign(payload_json)
            if not full_sig.startswith(sig_prefix):
                return None  # Tampered

            license_obj = LicenseKey(payload, full_sig)

            # Check expiration
            if license_obj.is_expired:
                return None

            # Cache for quick lookups
            self._active_licenses[payload.get("tenant_id", "")] = license_obj

            return license_obj

        except Exception:
            return None

    def get_active_license(self, tenant_id: str) -> Optional[LicenseKey]:
        """Get cached active license for a tenant."""
        return self._active_licenses.get(tenant_id)

    def has_feature(self, tenant_id: str, feature: str) -> bool:
        """Check if tenant's license includes a feature."""
        license_obj = self._active_licenses.get(tenant_id)
        if not license_obj:
            return False
        return feature in license_obj.features

    def record_usage(self, tenant_id: str, count: int = 1):
        """Record claim usage for metering."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if tenant_id not in self._usage_meters:
            self._usage_meters[tenant_id] = {}
        current = self._usage_meters[tenant_id].get(today, 0)
        self._usage_meters[tenant_id][today] = current + count

    def check_quota(self, tenant_id: str) -> Dict[str, Any]:
        """Check current usage against license quota."""
        license_obj = self._active_licenses.get(tenant_id)
        if not license_obj:
            return {"allowed": False, "reason": "no_active_license"}

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        used = self._usage_meters.get(tenant_id, {}).get(today, 0)
        limit = license_obj.max_claims_per_day

        return {
            "allowed": used < limit,
            "used_today": used,
            "daily_limit": limit,
            "remaining": max(0, limit - used),
            "utilization_pct": round((used / limit) * 100, 1) if limit > 0 else 0,
        }

    def get_usage_report(self, tenant_id: str, days: int = 30) -> Dict:
        """Get usage report for billing/analytics."""
        usage = self._usage_meters.get(tenant_id, {})
        license_obj = self._active_licenses.get(tenant_id)

        sorted_days = sorted(usage.keys(), reverse=True)[:days]
        daily_usage = {d: usage[d] for d in sorted_days}
        total = sum(daily_usage.values())

        return {
            "tenant_id": tenant_id,
            "period_days": days,
            "total_claims": total,
            "daily_breakdown": daily_usage,
            "license": license_obj.to_dict() if license_obj else None,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _default_features(self, tier: str) -> List[str]:
        """Get default feature set for a tier."""
        features = {
            "starter": ["verification", "audit"],
            "professional": ["verification", "audit", "export", "webhooks", "batch"],
            "enterprise": ["verification", "audit", "export", "webhooks", "batch",
                           "sso", "rbac", "white-label", "siem"],
            "government": ["verification", "audit", "export", "webhooks", "batch",
                           "sso", "rbac", "white-label", "siem", "data-residency",
                           "air-gap", "fips-140-3", "fedramp", "offline-license"],
        }
        return features.get(tier, features["starter"])


# Global singleton
license_manager = LicenseManager()
