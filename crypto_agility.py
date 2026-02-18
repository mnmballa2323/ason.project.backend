"""
Cryptographic Agility Framework — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Enables runtime algorithm migration without service disruption.
NASDAQ 100 Requirement: Ability to swap cryptographic algorithms
in response to emerging threats or new standards (e.g., PQC migration).

NIST SP 800-131A Rev. 2 / CNSA 2.0 aligned.
"""

import hashlib
import logging
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("qwen.crypto_agility")


class AlgorithmStatus(str, Enum):
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    TRANSITIONING = "transitioning"
    FORBIDDEN = "forbidden"
    EXPERIMENTAL = "experimental"


class AlgorithmFamily(str, Enum):
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    HASH = "hash"
    KDF = "kdf"
    MAC = "mac"
    KEM = "kem"
    SIGNATURE = "signature"


class CryptoAlgorithm:
    """A registered cryptographic algorithm with lifecycle metadata."""
    def __init__(self, alg_id, name, family, key_size,
                 status=AlgorithmStatus.APPROVED, successor=None,
                 sunset_date=None, nist_ref="", cnsa_compliant=False):
        self.alg_id = alg_id
        self.name = name
        self.family = family
        self.key_size = key_size
        self.status = status
        self.successor = successor  # Algorithm to migrate to
        self.sunset_date = sunset_date
        self.nist_ref = nist_ref
        self.cnsa_compliant = cnsa_compliant
        self.usage_count = 0
        self.registered_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "alg_id": self.alg_id, "name": self.name,
            "family": self.family.value, "key_size": self.key_size,
            "status": self.status.value, "successor": self.successor,
            "sunset_date": self.sunset_date, "cnsa_compliant": self.cnsa_compliant,
            "usage_count": self.usage_count,
        }


class MigrationPath:
    """A defined migration path from one algorithm to another."""
    def __init__(self, path_id, source_alg, target_alg,
                 reason, deadline, strategy="dual_write"):
        self.path_id = path_id
        self.source_alg = source_alg
        self.target_alg = target_alg
        self.reason = reason
        self.deadline = deadline
        self.strategy = strategy  # dual_write, rekey, proxy
        self.progress_pct = 0.0
        self.started = False
        self.completed = False

    def to_dict(self):
        return {
            "path_id": self.path_id,
            "from": self.source_alg, "to": self.target_alg,
            "reason": self.reason, "deadline": self.deadline,
            "strategy": self.strategy, "progress": self.progress_pct,
            "completed": self.completed,
        }


class CryptoAgilityFramework:
    """
    Runtime algorithm negotiation and migration.
    Supports hot-swap of crypto algorithms without downtime.
    """

    def __init__(self):
        self._algorithms: Dict[str, CryptoAlgorithm] = {}
        self._migrations: Dict[str, MigrationPath] = {}
        self._active_bindings: Dict[str, str] = {}  # purpose → alg_id
        self._lock = threading.Lock()
        self._register_algorithm_registry()

    def _register_algorithm_registry(self):
        A = CryptoAlgorithm
        F = AlgorithmFamily
        S = AlgorithmStatus

        # Symmetric encryption
        self.register(A("AES-256-GCM", "AES-256-GCM", F.SYMMETRIC, 256,
                         S.APPROVED, nist_ref="NIST SP 800-38D", cnsa_compliant=True))
        self.register(A("AES-128-GCM", "AES-128-GCM", F.SYMMETRIC, 128,
                         S.DEPRECATED, successor="AES-256-GCM",
                         sunset_date="2026-12-31", nist_ref="NIST SP 800-38D"))
        self.register(A("ChaCha20-Poly1305", "ChaCha20-Poly1305", F.SYMMETRIC, 256,
                         S.APPROVED, nist_ref="RFC 8439"))

        # Hash functions
        self.register(A("SHA-256", "SHA-256", F.HASH, 256,
                         S.APPROVED, nist_ref="FIPS 180-4", cnsa_compliant=True))
        self.register(A("SHA-384", "SHA-384", F.HASH, 384,
                         S.APPROVED, nist_ref="FIPS 180-4", cnsa_compliant=True))
        self.register(A("SHA-512", "SHA-512", F.HASH, 512,
                         S.APPROVED, nist_ref="FIPS 180-4", cnsa_compliant=True))
        self.register(A("SHA3-256", "SHA3-256", F.HASH, 256,
                         S.APPROVED, nist_ref="FIPS 202", cnsa_compliant=True))
        self.register(A("SHA-1", "SHA-1", F.HASH, 160,
                         S.FORBIDDEN, successor="SHA-256"))
        self.register(A("MD5", "MD5", F.HASH, 128,
                         S.FORBIDDEN, successor="SHA-256"))

        # Asymmetric — classical
        self.register(A("ECDSA-P384", "ECDSA P-384", F.SIGNATURE, 384,
                         S.TRANSITIONING, successor="ML-DSA-65",
                         sunset_date="2030-12-31", cnsa_compliant=True))
        self.register(A("RSA-4096", "RSA-4096", F.ASYMMETRIC, 4096,
                         S.TRANSITIONING, successor="ML-KEM-1024",
                         sunset_date="2030-12-31"))

        # Post-quantum — CNSA 2.0
        self.register(A("ML-KEM-1024", "ML-KEM-1024 (Kyber)", F.KEM, 256,
                         S.APPROVED, nist_ref="FIPS 203", cnsa_compliant=True))
        self.register(A("ML-DSA-65", "ML-DSA-65 (Dilithium)", F.SIGNATURE, 256,
                         S.APPROVED, nist_ref="FIPS 204", cnsa_compliant=True))
        self.register(A("SLH-DSA-256s", "SLH-DSA-SHA2-256s (SPHINCS+)", F.SIGNATURE, 256,
                         S.APPROVED, nist_ref="FIPS 205", cnsa_compliant=True))

        # KDF
        self.register(A("PBKDF2-SHA256", "PBKDF2-HMAC-SHA256", F.KDF, 256,
                         S.APPROVED, nist_ref="NIST SP 800-132"))
        self.register(A("HKDF-SHA256", "HKDF-SHA256", F.KDF, 256,
                         S.APPROVED, nist_ref="RFC 5869"))
        self.register(A("Argon2id", "Argon2id", F.KDF, 256,
                         S.APPROVED, nist_ref="RFC 9106"))

        # Default bindings
        self._active_bindings = {
            "encryption": "AES-256-GCM",
            "hashing": "SHA-384",
            "signing": "ECDSA-P384",
            "kdf": "PBKDF2-SHA256",
            "kem": "ML-KEM-1024",
            "pqc_signing": "ML-DSA-65",
        }

        # Pre-configure PQC migration paths
        self._migrations["MIG-001"] = MigrationPath(
            "MIG-001", "ECDSA-P384", "ML-DSA-65",
            "CNSA 2.0 post-quantum migration", "2030-12-31", "dual_write")
        self._migrations["MIG-002"] = MigrationPath(
            "MIG-002", "RSA-4096", "ML-KEM-1024",
            "CNSA 2.0 KEM migration", "2030-12-31", "rekey")

    def register(self, algorithm: CryptoAlgorithm):
        self._algorithms[algorithm.alg_id] = algorithm

    def resolve(self, purpose: str) -> Optional[CryptoAlgorithm]:
        """Resolve the active algorithm for a given purpose."""
        alg_id = self._active_bindings.get(purpose)
        if alg_id:
            alg = self._algorithms.get(alg_id)
            if alg:
                alg.usage_count += 1
            return alg
        return None

    def hot_swap(self, purpose: str, new_alg_id: str, actor: str):
        """Swap algorithm binding at runtime — zero downtime."""
        alg = self._algorithms.get(new_alg_id)
        if not alg:
            raise ValueError(f"Unknown algorithm: {new_alg_id}")
        if alg.status == AlgorithmStatus.FORBIDDEN:
            raise ValueError(f"Algorithm {new_alg_id} is FORBIDDEN")
        old = self._active_bindings.get(purpose)
        with self._lock:
            self._active_bindings[purpose] = new_alg_id
        logger.warning(f"CRYPTO HOT-SWAP: {purpose} changed from {old} → {new_alg_id} by {actor}")

    def get_cnsa_compliance(self) -> Dict:
        """CNSA 2.0 compliance status."""
        bindings = {}
        all_compliant = True
        for purpose, alg_id in self._active_bindings.items():
            alg = self._algorithms.get(alg_id)
            compliant = alg.cnsa_compliant if alg else False
            bindings[purpose] = {
                "algorithm": alg_id, "cnsa_compliant": compliant,
                "status": alg.status.value if alg else "unknown",
            }
            if not compliant:
                all_compliant = False
        return {
            "cnsa_2_0_compliant": all_compliant,
            "bindings": bindings,
            "forbidden_in_use": [
                a.alg_id for a in self._algorithms.values()
                if a.status == AlgorithmStatus.FORBIDDEN and a.usage_count > 0
            ],
            "pending_migrations": [m.to_dict() for m in self._migrations.values()
                                   if not m.completed],
        }

    def get_algorithm_inventory(self) -> Dict:
        return {
            "total": len(self._algorithms),
            "approved": sum(1 for a in self._algorithms.values()
                            if a.status == AlgorithmStatus.APPROVED),
            "deprecated": sum(1 for a in self._algorithms.values()
                              if a.status == AlgorithmStatus.DEPRECATED),
            "forbidden": sum(1 for a in self._algorithms.values()
                             if a.status == AlgorithmStatus.FORBIDDEN),
            "cnsa_compliant": sum(1 for a in self._algorithms.values()
                                  if a.cnsa_compliant),
            "algorithms": [a.to_dict() for a in self._algorithms.values()],
            "active_bindings": dict(self._active_bindings),
        }

crypto_agility = CryptoAgilityFramework()
