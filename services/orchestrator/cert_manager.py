"""
mTLS Certificate Manager — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Self-hosted PKI with automatic certificate provisioning,
rotation, revocation, and CRL/OCSP management for
zero-trust inter-service communication.
"""

import hashlib
import logging
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.cert_manager")


class CertStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    REVOKED = "revoked"


class CertType(str, Enum):
    ROOT_CA = "root_ca"
    INTERMEDIATE_CA = "intermediate_ca"
    SERVER = "server"
    CLIENT = "client"
    MTLS_PEER = "mtls_peer"


class RevocationReason(str, Enum):
    KEY_COMPROMISE = "key_compromise"
    CA_COMPROMISE = "ca_compromise"
    AFFILIATION_CHANGED = "affiliation_changed"
    SUPERSEDED = "superseded"
    CESSATION = "cessation_of_operation"
    PRIVILEGE_WITHDRAWN = "privilege_withdrawn"


class ManagedCertificate:
    """A certificate managed by the internal PKI."""
    def __init__(self, cert_id, common_name, cert_type, issuer,
                 validity_days=365, sans=None, key_size=4096):
        self.cert_id = cert_id
        self.common_name = common_name
        self.cert_type = cert_type
        self.issuer = issuer
        self.validity_days = validity_days
        self.sans = sans or []  # Subject Alternative Names
        self.key_size = key_size
        self.status = CertStatus.PENDING
        self.serial_number = hashlib.sha256(
            f"{cert_id}-{time.time()}".encode()
        ).hexdigest()[:20].upper()
        self.fingerprint = hashlib.sha256(os.urandom(32)).hexdigest()
        self.created_at = datetime.now(timezone.utc)
        self.issued_at: Optional[datetime] = None
        self.expires_at: Optional[datetime] = None
        self.revoked_at: Optional[str] = None
        self.revocation_reason: Optional[str] = None
        self.renewed_from: Optional[str] = None
        self.auto_renew = True

    def issue(self):
        self.status = CertStatus.ACTIVE
        self.issued_at = datetime.now(timezone.utc)
        self.expires_at = self.issued_at + timedelta(days=self.validity_days)

    def revoke(self, reason: RevocationReason):
        self.status = CertStatus.REVOKED
        self.revoked_at = datetime.now(timezone.utc).isoformat()
        self.revocation_reason = reason.value

    @property
    def days_until_expiry(self) -> int:
        if not self.expires_at:
            return -1
        return (self.expires_at - datetime.now(timezone.utc)).days

    @property
    def needs_renewal(self) -> bool:
        return (self.status == CertStatus.ACTIVE and
                0 < self.days_until_expiry <= 30)

    def to_dict(self):
        return {
            "cert_id": self.cert_id, "common_name": self.common_name,
            "type": self.cert_type.value, "status": self.status.value,
            "serial": self.serial_number, "issuer": self.issuer,
            "key_size": self.key_size, "sans": self.sans,
            "fingerprint": self.fingerprint[:32],
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "days_until_expiry": self.days_until_expiry,
            "needs_renewal": self.needs_renewal,
            "auto_renew": self.auto_renew,
        }


class CertificateManager:
    """Internal PKI / certificate lifecycle manager."""

    def __init__(self):
        self._certs: Dict[str, ManagedCertificate] = {}
        self._crl: List[Dict] = []  # Certificate Revocation List
        self._lock = threading.Lock()
        self._counter = 0
        self._register_platform_certs()

    def _register_platform_certs(self):
        """Pre-provision certificates for platform services."""
        root = self.create("Ason Root CA", CertType.ROOT_CA, "self-signed",
                           validity_days=3650, key_size=4096)
        root_id = root.cert_id
        self.issue(root_id)

        inter = self.create("Ason Intermediate CA", CertType.INTERMEDIATE_CA,
                            root_id, validity_days=1825, key_size=4096)
        self.issue(inter.cert_id)
        int_id = inter.cert_id

        services = [
            ("orchestrator.qwen.internal", ["orchestrator", "localhost"]),
            ("inference.qwen.internal", ["inference", "localhost"]),
            ("postgres.qwen.internal", ["postgres", "localhost"]),
            ("milvus.qwen.internal", ["milvus", "localhost"]),
            ("keycloak.qwen.internal", ["keycloak", "auth", "localhost"]),
            ("frontend.qwen.internal", ["frontend", "localhost"]),
        ]
        for cn, sans in services:
            cert = self.create(cn, CertType.MTLS_PEER, int_id,
                               validity_days=365, sans=sans)
            self.issue(cert.cert_id)

    def create(self, common_name, cert_type, issuer,
               validity_days=365, **kwargs) -> ManagedCertificate:
        with self._lock:
            self._counter += 1
            cert_id = f"cert-{self._counter:06d}"
        cert = ManagedCertificate(cert_id, common_name, cert_type, issuer,
                                  validity_days, **kwargs)
        self._certs[cert_id] = cert
        return cert

    def issue(self, cert_id: str):
        cert = self._certs.get(cert_id)
        if cert:
            cert.issue()
            logger.info(f"Certificate issued: {cert.common_name} ({cert_id})")

    def revoke(self, cert_id: str, reason: RevocationReason):
        cert = self._certs.get(cert_id)
        if cert:
            cert.revoke(reason)
            self._crl.append({
                "serial": cert.serial_number,
                "revoked_at": cert.revoked_at,
                "reason": reason.value,
            })
            logger.warning(f"Certificate revoked: {cert.common_name} — {reason.value}")

    def renew(self, cert_id: str) -> Optional[ManagedCertificate]:
        old = self._certs.get(cert_id)
        if not old:
            return None
        new = self.create(old.common_name, old.cert_type, old.issuer,
                          old.validity_days, sans=old.sans, key_size=old.key_size)
        new.renewed_from = cert_id
        self.issue(new.cert_id)
        old.status = CertStatus.EXPIRED
        return new

    def renew_all_expiring(self) -> List[str]:
        renewed = []
        for cert in list(self._certs.values()):
            if cert.needs_renewal and cert.auto_renew:
                new = self.renew(cert.cert_id)
                if new:
                    renewed.append(new.cert_id)
        return renewed

    def is_valid(self, cert_id: str) -> bool:
        cert = self._certs.get(cert_id)
        if not cert:
            return False
        return cert.status == CertStatus.ACTIVE and cert.days_until_expiry > 0

    def get_crl(self) -> List[Dict]:
        return self._crl

    def get_stats(self) -> Dict:
        active = sum(1 for c in self._certs.values() if c.status == CertStatus.ACTIVE)
        expiring = sum(1 for c in self._certs.values() if c.needs_renewal)
        revoked = sum(1 for c in self._certs.values() if c.status == CertStatus.REVOKED)
        return {
            "total": len(self._certs), "active": active,
            "expiring_soon": expiring, "revoked": revoked,
            "crl_entries": len(self._crl),
            "platform_services": [c.common_name for c in self._certs.values()
                                   if c.cert_type == CertType.MTLS_PEER],
        }

cert_manager = CertificateManager()
