"""
Next-Gen Identity & Access — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

FIDO2/WebAuthn passwordless authentication, Decentralized Identity (DID),
Just-In-Time privileged access, Continuous Adaptive Trust Scoring.
"""

import hashlib
import logging
import os
import time
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.nextgen_identity")


# ============================================================================
#  FIDO2/WebAuthn — Passwordless
# ============================================================================

class AuthenticatorType(str, Enum):
    PLATFORM = "platform"       # Built-in (Windows Hello, Touch ID)
    CROSS_PLATFORM = "cross_platform"  # USB/NFC key (YubiKey)
    HYBRID = "hybrid"           # Phone-as-authenticator


class WebAuthnCredential:
    def __init__(self, cred_id, user_id, authenticator,
                 public_key_hash, attestation="none"):
        self.cred_id = cred_id
        self.user_id = user_id
        self.authenticator = authenticator
        self.public_key_hash = public_key_hash
        self.attestation = attestation
        self.sign_count = 0
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_used: Optional[str] = None
        self.revoked = False

    def to_dict(self):
        return {
            "cred_id": self.cred_id[:16] + "...",
            "authenticator": self.authenticator.value,
            "sign_count": self.sign_count,
            "last_used": self.last_used, "revoked": self.revoked,
        }


class FIDO2Service:
    """FIDO2/WebAuthn passwordless authentication."""

    def __init__(self):
        self._credentials: Dict[str, WebAuthnCredential] = {}
        self._challenges: Dict[str, str] = {}

    def begin_registration(self, user_id: str) -> Dict:
        challenge = os.urandom(32).hex()
        self._challenges[user_id] = challenge
        return {
            "challenge": challenge,
            "rp": {"id": "qwen.ai", "name": "Ason Verification Platform"},
            "user": {"id": user_id},
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},   # ES256
                {"type": "public-key", "alg": -257},  # RS256
            ],
            "attestation": "direct",
            "authenticatorSelection": {
                "residentKey": "preferred",
                "userVerification": "required",
            },
        }

    def complete_registration(self, user_id: str, cred_id: str,
                              authenticator: AuthenticatorType) -> WebAuthnCredential:
        pk_hash = hashlib.sha256(f"{cred_id}:{os.urandom(16).hex()}".encode()).hexdigest()
        cred = WebAuthnCredential(cred_id, user_id, authenticator, pk_hash)
        self._credentials[cred_id] = cred
        return cred

    def begin_authentication(self, user_id: str) -> Dict:
        challenge = os.urandom(32).hex()
        self._challenges[user_id] = challenge
        user_creds = [c for c in self._credentials.values()
                      if c.user_id == user_id and not c.revoked]
        return {
            "challenge": challenge,
            "allowCredentials": [{"id": c.cred_id, "type": "public-key"}
                                  for c in user_creds],
            "userVerification": "required",
        }

    def verify_authentication(self, cred_id: str, sign_count: int) -> Dict:
        cred = self._credentials.get(cred_id)
        if not cred or cred.revoked:
            return {"verified": False, "reason": "Invalid credential"}
        if sign_count <= cred.sign_count:
            return {"verified": False, "reason": "Cloned authenticator detected"}
        cred.sign_count = sign_count
        cred.last_used = datetime.now(timezone.utc).isoformat()
        return {"verified": True, "user_id": cred.user_id}


# ============================================================================
#  DECENTRALIZED IDENTITY (DID/VC)
# ============================================================================

class DIDMethod(str, Enum):
    DID_KEY = "did:key"
    DID_WEB = "did:web"
    DID_ION = "did:ion"


class VerifiableCredential:
    def __init__(self, vc_id, issuer_did, subject_did,
                 credential_type, claims, expiry=None):
        self.vc_id = vc_id
        self.issuer_did = issuer_did
        self.subject_did = subject_did
        self.credential_type = credential_type
        self.claims = claims
        self.expiry = expiry
        self.issuance_date = datetime.now(timezone.utc).isoformat()
        self.proof_hash = hashlib.sha256(
            f"{vc_id}:{issuer_did}:{subject_did}".encode()
        ).hexdigest()
        self.revoked = False

    def to_dict(self):
        return {
            "vc_id": self.vc_id, "type": self.credential_type,
            "issuer": self.issuer_did[:30], "subject": self.subject_did[:30],
            "claims": list(self.claims.keys()),
            "revoked": self.revoked,
        }


class DecentralizedIdentityService:
    """W3C DID/VC management."""

    def __init__(self):
        self._dids: Dict[str, Dict] = {}
        self._vcs: Dict[str, VerifiableCredential] = {}
        self._counter = 0

    def create_did(self, method: DIDMethod = DIDMethod.DID_KEY,
                   controller: str = "") -> Dict:
        key_material = os.urandom(32).hex()
        did = f"{method.value}:{hashlib.sha256(key_material.encode()).hexdigest()[:32]}"
        doc = {
            "id": did, "method": method.value,
            "controller": controller or did,
            "verificationMethod": [{
                "id": f"{did}#key-1", "type": "Ed25519VerificationKey2020",
                "publicKeyMultibase": f"z{key_material[:44]}",
            }],
            "created": datetime.now(timezone.utc).isoformat(),
        }
        self._dids[did] = doc
        return doc

    def issue_credential(self, issuer_did: str, subject_did: str,
                         cred_type: str, claims: Dict) -> VerifiableCredential:
        self._counter += 1
        vc_id = f"VC-{self._counter:08d}"
        vc = VerifiableCredential(vc_id, issuer_did, subject_did,
                                 cred_type, claims)
        self._vcs[vc_id] = vc
        return vc

    def verify_credential(self, vc_id: str) -> Dict:
        vc = self._vcs.get(vc_id)
        if not vc:
            return {"valid": False, "reason": "Credential not found"}
        if vc.revoked:
            return {"valid": False, "reason": "Credential revoked"}
        return {"valid": True, "vc_id": vc_id, "type": vc.credential_type}


# ============================================================================
#  JUST-IN-TIME PRIVILEGED ACCESS
# ============================================================================

class JITSession:
    def __init__(self, session_id, user_id, role, duration_minutes,
                 justification, approver):
        self.session_id = session_id
        self.user_id = user_id
        self.role = role
        self.duration_minutes = duration_minutes
        self.justification = justification
        self.approver = approver
        self.granted_at = datetime.now(timezone.utc)
        self.expires_at_ts = self.granted_at.timestamp() + duration_minutes * 60
        self.revoked = False
        self.actions_performed: List[str] = []

    @property
    def expired(self):
        return time.time() > self.expires_at_ts

    @property
    def active(self):
        return not self.expired and not self.revoked

    def to_dict(self):
        return {
            "session_id": self.session_id, "user": self.user_id,
            "role": self.role, "duration_min": self.duration_minutes,
            "active": self.active, "revoked": self.revoked,
            "actions": len(self.actions_performed),
        }


class JITAccessService:
    """Ephemeral privileged access that auto-expires."""

    def __init__(self):
        self._sessions: Dict[str, JITSession] = {}
        self._counter = 0

    def request_access(self, user_id: str, role: str,
                       duration_minutes: int, justification: str,
                       approver: str) -> JITSession:
        self._counter += 1
        sess_id = f"JIT-{self._counter:08d}"
        session = JITSession(sess_id, user_id, role, duration_minutes,
                            justification, approver)
        self._sessions[sess_id] = session
        logger.warning(f"JIT access granted: {user_id} → {role} for {duration_minutes}min")
        return session

    def check_access(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        return session.active if session else False

    def revoke(self, session_id: str, reason: str = ""):
        session = self._sessions.get(session_id)
        if session:
            session.revoked = True
            logger.info(f"JIT session {session_id} revoked: {reason}")


# ============================================================================
#  CONTINUOUS ADAPTIVE TRUST SCORING
# ============================================================================

class TrustFactor(str, Enum):
    DEVICE_POSTURE = "device_posture"
    LOCATION = "location"
    BEHAVIOR = "behavior"
    TIME_OF_DAY = "time_of_day"
    AUTH_METHOD = "auth_method"
    SESSION_AGE = "session_age"
    RISK_INDICATORS = "risk_indicators"


class AdaptiveTrustEngine:
    """Real-time user trust scoring that adjusts access dynamically."""

    def __init__(self):
        self._scores: Dict[str, float] = {}
        self._factor_weights = {
            TrustFactor.DEVICE_POSTURE: 0.20,
            TrustFactor.LOCATION: 0.15,
            TrustFactor.BEHAVIOR: 0.25,
            TrustFactor.TIME_OF_DAY: 0.05,
            TrustFactor.AUTH_METHOD: 0.15,
            TrustFactor.SESSION_AGE: 0.10,
            TrustFactor.RISK_INDICATORS: 0.10,
        }

    def calculate_trust(self, user_id: str, factors: Dict[TrustFactor, float]) -> Dict:
        """Calculate composite trust score (0.0-1.0)."""
        score = 0.0
        breakdown = {}
        for factor, weight in self._factor_weights.items():
            value = factors.get(factor, 0.5)
            weighted = value * weight
            score += weighted
            breakdown[factor.value] = round(weighted, 3)

        self._scores[user_id] = score
        access_level = "full" if score >= 0.8 else "limited" if score >= 0.5 else "denied"

        return {
            "user_id": user_id, "trust_score": round(score, 3),
            "access_level": access_level, "breakdown": breakdown,
        }


# Singleton instances
fido2_service = FIDO2Service()
did_service = DecentralizedIdentityService()
jit_access = JITAccessService()
trust_engine = AdaptiveTrustEngine()
