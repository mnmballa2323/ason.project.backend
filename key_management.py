"""
Enterprise Key Management — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
NIST SP 800-57 Part 1: Key Management
"""
import hashlib, json, logging, os, secrets, time, threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("qwen.key_management")

class KeyType(str, Enum):
    AES_256 = "AES-256"
    ECDSA_P256 = "ECDSA-P256"
    ECDSA_P384 = "ECDSA-P384"
    RSA_4096 = "RSA-4096"
    HMAC = "HMAC-SHA-256"

class KeyPurpose(str, Enum):
    ENCRYPTION = "encryption"
    SIGNING = "signing"
    AUTHENTICATION = "authentication"
    KEY_WRAPPING = "key_wrapping"

class KeyState(str, Enum):
    PRE_ACTIVATION = "pre_activation"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    COMPROMISED = "compromised"
    DESTROYED = "destroyed"

class KeyStorageBackend(str, Enum):
    SOFTWARE = "software"
    HSM = "hsm"
    VAULT = "vault"

class ManagedKey:
    def __init__(self, key_id, key_type, purpose, owner, tenant_id="",
                 backend=KeyStorageBackend.SOFTWARE, rotation_days=365):
        self.key_id = key_id
        self.key_type = key_type
        self.purpose = purpose
        self.owner = owner
        self.tenant_id = tenant_id
        self.backend = backend
        self.rotation_days = rotation_days
        self.state = KeyState.PRE_ACTIVATION
        self.version = 1
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.activated_at = None
        self.last_rotated = None
        self.usage_count = 0
        self._key_material = None
        self.fingerprint = ""

    def activate(self):
        self.state = KeyState.ACTIVE
        self.activated_at = datetime.now(timezone.utc).isoformat()

    def deactivate(self):
        self.state = KeyState.DEACTIVATED

    def destroy(self):
        self.state = KeyState.DESTROYED
        if self._key_material:
            self._key_material = b'\x00' * len(self._key_material)
            self._key_material = None

    def mark_compromised(self, reason):
        self.state = KeyState.COMPROMISED
        logger.critical(f"KEY COMPROMISED: {self.key_id} — {reason}")

    @property
    def needs_rotation(self):
        if self.state != KeyState.ACTIVE or not self.activated_at:
            return False
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(self.activated_at)).days
        return age >= self.rotation_days

    def to_dict(self):
        return {
            "key_id": self.key_id, "key_type": self.key_type.value,
            "purpose": self.purpose.value, "state": self.state.value,
            "owner": self.owner, "version": self.version,
            "backend": self.backend.value, "fingerprint": self.fingerprint,
            "needs_rotation": self.needs_rotation if self.state == KeyState.ACTIVE else False,
            "usage_count": self.usage_count,
        }

class KeyManagementService:
    def __init__(self):
        self._keys: Dict[str, ManagedKey] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def generate_key(self, key_type, purpose, owner, tenant_id="",
                     auto_activate=True, rotation_days=365):
        with self._lock:
            self._counter += 1
            key_id = f"key-{self._counter:08d}"
        key = ManagedKey(key_id, key_type, purpose, owner, tenant_id,
                         rotation_days=rotation_days)
        key._key_material = os.urandom(32)
        key.fingerprint = hashlib.sha256(key._key_material).hexdigest()[:16]
        if auto_activate:
            key.activate()
        self._keys[key_id] = key
        return key

    def rotate_key(self, key_id, actor):
        old = self._keys.get(key_id)
        if not old:
            raise ValueError(f"Key not found: {key_id}")
        new = self.generate_key(old.key_type, old.purpose, old.owner,
                                old.tenant_id, rotation_days=old.rotation_days)
        new.version = old.version + 1
        new.last_rotated = datetime.now(timezone.utc).isoformat()
        old.deactivate()
        return new

    def destroy_key(self, key_id, actor):
        key = self._keys.get(key_id)
        if key:
            key.destroy()

    def get_compliance_report(self):
        active = [k for k in self._keys.values() if k.state == KeyState.ACTIVE]
        return {
            "total": len(self._keys), "active": len(active),
            "needs_rotation": sum(1 for k in active if k.needs_rotation),
            "compromised": sum(1 for k in self._keys.values() if k.state == KeyState.COMPROMISED),
            "nist_ref": "NIST SP 800-57 Part 1 Rev. 5",
        }

key_management = KeyManagementService()
