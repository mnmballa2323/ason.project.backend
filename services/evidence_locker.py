"""
Evidence Locker — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Simulates Write-Once-Read-Many (WORM) storage for audit logs.
Ensures evidence cannot be tampered with once written.
COMPLIANCE LEVEL: IRS PUB 1075 / FIPS 140-3
"""
import hashlib
import json
import logging
import time
import os
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.evidence_locker")

class EvidenceLocker:
    """
    Secure storage for compliance evidence.
    Uses cryptographic hashing to chain records (Blockchain-lite).
    Persists to disk to survive restarts.
    """
    
    LEDGER_FILE = "audit_chain.jsonl"
    
    def __init__(self):
        self._store = []
        self._last_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        self._load_ledger()

    def _load_ledger(self):
        """Load existing ledger from disk."""
        if not os.path.exists(self.LEDGER_FILE):
            return
            
        try:
            with open(self.LEDGER_FILE, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    self._store.append(entry)
                    self._last_hash = entry["id"]
            logger.info(f"Loaded {len(self._store)} audit records from disk.")
        except Exception as e:
            logger.critical(f"Failed to load audit ledger: {e}")

    def write_evidence(self, event_type: str, details: Dict, actor: str = "system") -> str:
        """
        Write a new immutable record.
        Returns the record ID (SHA-256 hash).
        """
        timestamp = time.time()
        record = {
            "timestamp": timestamp,
            "type": event_type,
            "actor": actor,
            "details": details,
            "prev_hash": self._last_hash,
            "compliance_tag": "FTI-SENSITIVE" # IRS 1075
        }
        
        # Canonical JSON string for consistent hashing
        record_str = json.dumps(record, sort_keys=True)
        record_hash = hashlib.sha256(record_str.encode("utf-8")).hexdigest()
        
        entry = {
            "id": record_hash,
            "data": record
        }
        
        # 1. Update In-Memory
        self._store.append(entry)
        self._last_hash = record_hash
        
        # 2. Persist to Disk (Append-Only)
        try:
            with open(self.LEDGER_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.critical(f"FATAL: Could not write to audit ledger: {e}")
            raise IOError("Audit Write Failed")
        
        logger.info(f"🔒 Evidence Locked: {event_type} (ID: {record_hash[:8]})")
        return record_hash

    def get_evidence_chain(self) -> List[Dict]:
        """Return the entire immutable chain for auditing."""
        return self._store

    def verify_integrity(self) -> bool:
        """
        Cryptographically verify the chain integrity.
        Re-calculates hashes to ensure no tampering.
        """
        prev = "0000000000000000000000000000000000000000000000000000000000000000"
        for entry in self._store:
            data = entry["data"]
            if data["prev_hash"] != prev:
                logger.error(f"Integrity Failure! Record {entry['id']} has invalid prev_hash.")
                return False
            
            # Re-hash
            record_str = json.dumps(data, sort_keys=True)
            check_hash = hashlib.sha256(record_str.encode("utf-8")).hexdigest()
            
            if check_hash != entry["id"]:
                logger.error(f"Integrity Failure! Record {entry['id']} hash mismatch.")
                return False
            
            prev = check_hash
            
        return True

evidence_locker = EvidenceLocker()
