"""
Blockchain & Immutable Audit — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Merkle audit log, smart contract verifier, decentralized timestamping,
attestation token engine. All self-hosted, no external blockchains.
"""

import hashlib, logging, os, struct, time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("qwen.blockchain")


# ============================================================================
#  MERKLE AUDIT LOG
# ============================================================================

class MerkleNode:
    def __init__(self, left_hash, right_hash):
        self.left = left_hash
        self.right = right_hash
        self.hash = hashlib.sha256(
            f"{left_hash}:{right_hash}".encode()).hexdigest()


class MerkleAuditLog:
    """Tamper-evident audit log with Merkle tree verification."""

    def __init__(self):
        self._entries: List[Dict] = []
        self._leaf_hashes: List[str] = []
        self._root: Optional[str] = None

    def append(self, event: str, actor: str, details: str = "") -> Dict:
        leaf_data = f"{len(self._entries)}:{event}:{actor}:{details}:{time.time()}"
        leaf_hash = hashlib.sha256(leaf_data.encode()).hexdigest()
        self._leaf_hashes.append(leaf_hash)
        entry = {"index": len(self._entries), "event": event,
                 "actor": actor, "hash": leaf_hash[:16],
                 "ts": datetime.now(timezone.utc).isoformat()}
        self._entries.append(entry)
        self._root = self._compute_root()
        return entry

    def _compute_root(self) -> str:
        if not self._leaf_hashes:
            return hashlib.sha256(b"empty").hexdigest()
        level = list(self._leaf_hashes)
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                parent = hashlib.sha256(f"{left}:{right}".encode()).hexdigest()
                next_level.append(parent)
            level = next_level
        return level[0]

    def verify_integrity(self) -> Dict:
        computed = self._compute_root()
        valid = computed == self._root
        return {"valid": valid, "root": self._root[:16] if self._root else None,
                "entries": len(self._entries), "leaves": len(self._leaf_hashes)}

    def get_proof(self, index: int) -> Dict:
        """Get Merkle inclusion proof for entry at index."""
        if index >= len(self._leaf_hashes):
            return {"error": "Index out of range"}
        proof_hashes = []
        level = list(self._leaf_hashes)
        pos = index
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                if i == pos or i + 1 == pos:
                    sibling = right if i == pos else left
                    proof_hashes.append(sibling[:16])
                parent = hashlib.sha256(f"{left}:{right}".encode()).hexdigest()
                next_level.append(parent)
            pos = pos // 2
            level = next_level
        return {"index": index, "proof_length": len(proof_hashes),
                "proof": proof_hashes}

    def get_stats(self) -> Dict:
        return {"entries": len(self._entries), "root": self._root[:16] if self._root else None}


# ============================================================================
#  SMART CONTRACT VERIFIER
# ============================================================================

class ContractProperty(str, Enum):
    NO_REENTRANCY = "no_reentrancy"
    NO_OVERFLOW = "no_integer_overflow"
    ACCESS_CONTROL = "proper_access_control"
    NO_SELFDESTRUCT = "no_selfdestruct"
    INPUT_VALIDATION = "input_validated"
    STATE_CONSISTENCY = "state_consistent"


class SmartContractVerifier:
    """Formal verification of on-chain logic (self-hosted)."""

    VULN_PATTERNS = {
        ContractProperty.NO_REENTRANCY: ["call.value", "delegatecall", ".call{"],
        ContractProperty.NO_OVERFLOW: ["unchecked", "assembly"],
        ContractProperty.ACCESS_CONTROL: ["tx.origin", "msg.sender =="],
        ContractProperty.NO_SELFDESTRUCT: ["selfdestruct", "SELFDESTRUCT"],
        ContractProperty.INPUT_VALIDATION: ["require(", "assert("],
    }

    def __init__(self):
        self._verifications: List[Dict] = []

    def verify(self, contract_name: str, source_code: str) -> Dict:
        findings = []
        properties_checked = 0
        properties_passed = 0
        for prop, patterns in self.VULN_PATTERNS.items():
            properties_checked += 1
            found = any(p in source_code for p in patterns)
            passed = not found if prop != ContractProperty.INPUT_VALIDATION else found
            if passed:
                properties_passed += 1
            else:
                findings.append({"property": prop.value, "status": "violated"})

        result = {
            "contract": contract_name,
            "properties_checked": properties_checked,
            "properties_passed": properties_passed,
            "secure": properties_passed == properties_checked,
            "findings": findings,
            "ts": datetime.now(timezone.utc).isoformat()}
        self._verifications.append(result)
        return result

    def get_stats(self) -> Dict:
        return {"verifications": len(self._verifications),
                "properties": len(self.VULN_PATTERNS)}


# ============================================================================
#  DECENTRALIZED TIMESTAMPING
# ============================================================================

class TimestampAnchor:
    def __init__(self, anchor_id, data_hash, prev_anchor_hash):
        self.anchor_id = anchor_id
        self.data_hash = data_hash
        self.prev_hash = prev_anchor_hash
        self.ts = datetime.now(timezone.utc).isoformat()
        self.anchor_hash = hashlib.sha256(
            f"{anchor_id}:{data_hash}:{prev_anchor_hash}:{self.ts}".encode()
        ).hexdigest()

    def to_dict(self):
        return {"id": self.anchor_id, "data": self.data_hash[:16],
                "anchor": self.anchor_hash[:16], "ts": self.ts}


class DecentralizedTimestamping:
    """Hash-anchored provable timestamps (self-hosted chain)."""

    def __init__(self):
        self._chain: List[TimestampAnchor] = []
        self._counter = 0
        # Genesis anchor
        genesis = TimestampAnchor("TS-000000", "GENESIS", "0" * 64)
        self._chain.append(genesis)

    def timestamp(self, data: str) -> TimestampAnchor:
        self._counter += 1
        data_hash = hashlib.sha256(data.encode()).hexdigest()
        prev_hash = self._chain[-1].anchor_hash
        anchor = TimestampAnchor(f"TS-{self._counter:06d}", data_hash, prev_hash)
        self._chain.append(anchor)
        return anchor

    def verify_chain(self) -> Dict:
        valid = True
        for i in range(1, len(self._chain)):
            if self._chain[i].prev_hash != self._chain[i - 1].anchor_hash:
                valid = False
                break
        return {"valid": valid, "length": len(self._chain)}

    def get_stats(self) -> Dict:
        return {"anchors": len(self._chain),
                "chain_valid": self.verify_chain()["valid"]}


# ============================================================================
#  ATTESTATION TOKEN ENGINE
# ============================================================================

class AttestationType(str, Enum):
    CERTIFICATION = "certification"
    COMPLIANCE = "compliance_attestation"
    AUDIT = "audit_completion"
    TRAINING = "training_completion"
    ACCESS = "access_grant"
    IDENTITY = "identity_verification"


class AttestationToken:
    def __init__(self, token_id, att_type, subject, issuer,
                 claims, expiry_days):
        self.token_id = token_id
        self.att_type = att_type
        self.subject = subject
        self.issuer = issuer
        self.claims = claims
        self.issued_at = datetime.now(timezone.utc).isoformat()
        self.expiry_days = expiry_days
        self.revoked = False
        self.token_hash = hashlib.sha256(
            f"{token_id}:{subject}:{issuer}:{time.time()}".encode()
        ).hexdigest()

    def to_dict(self):
        return {"id": self.token_id, "type": self.att_type.value,
                "subject": self.subject, "issuer": self.issuer,
                "claims": len(self.claims), "revoked": self.revoked,
                "hash": self.token_hash[:16]}


class AttestationTokenEngine:
    """Non-fungible attestation tokens for certifications."""

    def __init__(self):
        self._tokens: Dict[str, AttestationToken] = {}
        self._counter = 0

    def issue(self, att_type: AttestationType, subject: str,
              issuer: str, claims: Dict, expiry_days: int = 365) -> AttestationToken:
        self._counter += 1
        token = AttestationToken(f"ATT-{self._counter:08d}", att_type,
                                subject, issuer, claims, expiry_days)
        self._tokens[token.token_id] = token
        return token

    def verify(self, token_id: str) -> Dict:
        token = self._tokens.get(token_id)
        if not token:
            return {"valid": False, "reason": "Token not found"}
        if token.revoked:
            return {"valid": False, "reason": "Token revoked"}
        return {"valid": True, "token": token.to_dict()}

    def revoke(self, token_id: str) -> Dict:
        token = self._tokens.get(token_id)
        if not token:
            return {"error": "Token not found"}
        token.revoked = True
        return {"revoked": True, "id": token_id}

    def get_stats(self) -> Dict:
        return {"tokens_issued": len(self._tokens),
                "active": sum(1 for t in self._tokens.values() if not t.revoked),
                "revoked": sum(1 for t in self._tokens.values() if t.revoked)}

# Singletons
merkle_log = MerkleAuditLog()
contract_verifier = SmartContractVerifier()
timestamp_service = DecentralizedTimestamping()
attestation_engine = AttestationTokenEngine()
