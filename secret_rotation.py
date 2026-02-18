"""
Secret Rotation — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Automated zero-downtime rotation of DB passwords, JWT keys, and license secrets.
Uses a dual-key overlap window so active sessions are never interrupted.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("qwen.secret_rotation")


# ============================================================================
#  SECRET TYPES
# ============================================================================

class SecretType:
    DB_PASSWORD = "db_password"
    JWT_SIGNING_KEY = "jwt_signing_key"
    LICENSE_SECRET = "license_secret"
    WEBHOOK_SECRET = "webhook_secret"
    BACKUP_KEY = "backup_encryption_key"
    SESSION_SECRET = "session_secret"


class SecretVersion:
    """A single version of a secret with metadata."""

    def __init__(self, value: str, created_at: float = None, expires_at: float = None, version: int = 0):
        self.value = value
        self.created_at = created_at or time.time()
        self.expires_at = expires_at  # None = no expiration
        self.version = version
        self.is_active = True

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
            "expires_at": datetime.fromtimestamp(self.expires_at, tz=timezone.utc).isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "is_expired": self.is_expired,
            "fingerprint": hashlib.sha256(self.value.encode()).hexdigest()[:16],
        }


# ============================================================================
#  SECRET STORE
# ============================================================================

class ManagedSecret:
    """
    Manages a single secret with dual-key overlap rotation.

    During rotation:
    1. New key is generated
    2. Both old and new keys are active (overlap window)
    3. After overlap period, old key is retired
    4. Consumers that validate should check BOTH keys during overlap
    """

    def __init__(self, name: str, rotation_days: int = 90, overlap_hours: int = 24):
        self.name = name
        self.rotation_days = rotation_days
        self.overlap_hours = overlap_hours
        self._versions: List[SecretVersion] = []
        self._version_counter: int = 0
        self._on_rotate_callbacks: List[Callable] = []

    @property
    def current(self) -> Optional[SecretVersion]:
        active = [v for v in self._versions if v.is_active and not v.is_expired]
        return active[-1] if active else None

    @property
    def all_active(self) -> List[SecretVersion]:
        """All currently active (non-expired) versions — used during overlap window."""
        return [v for v in self._versions if v.is_active and not v.is_expired]

    def initialize(self, value: str):
        """Set the initial secret value."""
        self._version_counter += 1
        version = SecretVersion(value=value, version=self._version_counter)
        self._versions.append(version)
        logger.info(f"Secret '{self.name}' initialized (v{self._version_counter})")

    def rotate(self, new_value: str = None) -> SecretVersion:
        """
        Rotate the secret.
        - Generates a new value (or uses provided)
        - Old value remains active during overlap window
        - Triggers on_rotate callbacks
        """
        if new_value is None:
            new_value = secrets.token_hex(32)

        self._version_counter += 1

        # Set old versions to expire after overlap window
        overlap_seconds = self.overlap_hours * 3600
        for v in self._versions:
            if v.is_active and v.expires_at is None:
                v.expires_at = time.time() + overlap_seconds

        # Create new version
        new_version = SecretVersion(
            value=new_value,
            version=self._version_counter,
        )
        self._versions.append(new_version)

        logger.info(
            f"Secret '{self.name}' rotated → v{self._version_counter} "
            f"(overlap: {self.overlap_hours}h, old versions: {len(self.all_active)})"
        )

        # Notify consumers
        for callback in self._on_rotate_callbacks:
            try:
                callback(self.name, new_version)
            except Exception as e:
                logger.error(f"Rotation callback error for '{self.name}': {e}")

        return new_version

    def needs_rotation(self) -> bool:
        """Check if this secret is due for rotation."""
        current = self.current
        if not current:
            return True
        age_days = (time.time() - current.created_at) / 86400
        return age_days >= self.rotation_days

    def cleanup_expired(self):
        """Remove expired versions."""
        before = len(self._versions)
        self._versions = [v for v in self._versions if not v.is_expired]
        removed = before - len(self._versions)
        if removed:
            logger.info(f"Secret '{self.name}': cleaned up {removed} expired version(s)")

    def validate_against_any(self, test_value: str) -> bool:
        """Validate a value against any active version (for dual-key overlap)."""
        for v in self.all_active:
            if hmac.compare_digest(v.value, test_value):
                return True
        return False

    def on_rotate(self, callback: Callable):
        """Register a callback for rotation events."""
        self._on_rotate_callbacks.append(callback)

    def get_status(self) -> dict:
        current = self.current
        return {
            "name": self.name,
            "rotation_days": self.rotation_days,
            "overlap_hours": self.overlap_hours,
            "current_version": current.version if current else None,
            "active_versions": len(self.all_active),
            "total_versions": len(self._versions),
            "needs_rotation": self.needs_rotation(),
            "age_days": round((time.time() - current.created_at) / 86400, 1) if current else None,
            "versions": [v.to_dict() for v in self._versions[-5:]],  # Last 5
        }


# ============================================================================
#  SECRET ROTATION MANAGER
# ============================================================================

class SecretRotationManager:
    """
    Manages all rotatable secrets across the platform.
    Provides a unified interface for rotation, validation, and monitoring.
    """

    def __init__(self):
        self._secrets: Dict[str, ManagedSecret] = {}
        self._rotation_log: List[Dict] = []

        # Register default secrets
        self._register_defaults()

    def _register_defaults(self):
        """Register platform secrets with rotation policies."""
        self.register(SecretType.JWT_SIGNING_KEY, rotation_days=30, overlap_hours=48)
        self.register(SecretType.DB_PASSWORD, rotation_days=90, overlap_hours=24)
        self.register(SecretType.LICENSE_SECRET, rotation_days=365, overlap_hours=168)  # 7 day overlap
        self.register(SecretType.WEBHOOK_SECRET, rotation_days=60, overlap_hours=24)
        self.register(SecretType.BACKUP_KEY, rotation_days=180, overlap_hours=48)
        self.register(SecretType.SESSION_SECRET, rotation_days=14, overlap_hours=4)

    def register(self, name: str, rotation_days: int = 90, overlap_hours: int = 24):
        """Register a secret for managed rotation."""
        self._secrets[name] = ManagedSecret(name, rotation_days, overlap_hours)

        # Initialize from environment if available
        env_key = f"ASON_{name.upper()}"
        env_value = os.getenv(env_key)
        if env_value:
            self._secrets[name].initialize(env_value)

    def rotate(self, name: str, new_value: str = None) -> SecretVersion:
        """Rotate a specific secret."""
        if name not in self._secrets:
            raise ValueError(f"Unknown secret: {name}")

        result = self._secrets[name].rotate(new_value)

        self._rotation_log.append({
            "secret": name,
            "version": result.version,
            "rotated_at": datetime.now(timezone.utc).isoformat(),
        })

        return result

    def rotate_all_due(self) -> List[str]:
        """Rotate all secrets that are due for rotation."""
        rotated = []
        for name, secret in self._secrets.items():
            if secret.needs_rotation():
                secret.rotate()
                rotated.append(name)
        return rotated

    def validate(self, name: str, value: str) -> bool:
        """Validate a value against any active version of a secret."""
        if name not in self._secrets:
            return False
        return self._secrets[name].validate_against_any(value)

    def get_status(self) -> Dict:
        """Get rotation status for all secrets."""
        return {
            name: secret.get_status()
            for name, secret in self._secrets.items()
        }

    def get_rotation_log(self, limit: int = 50) -> List[Dict]:
        return self._rotation_log[-limit:]

    def cleanup(self):
        """Clean up expired secret versions."""
        for secret in self._secrets.values():
            secret.cleanup_expired()


# Global singleton
secret_manager = SecretRotationManager()
