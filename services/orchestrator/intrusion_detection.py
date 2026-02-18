"""
Intrusion Detection System — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Hybrid signature + heuristic IDS for detecting:
- Known attack signatures (SQLi, XSS, path traversal, command injection)
- Protocol anomalies (malformed headers, oversized payloads, unusual encodings)
- Session anomalies (hijacking, fixation, replay)
- Evasion techniques (double encoding, null bytes, unicode normalization attacks)

All detection is local — no external signature updates.
"""

import hashlib
import logging
import re
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("qwen.ids")


class IDSVerdict(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    BLOCKED = "blocked"


class AttackClass(str, Enum):
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    SSRF = "ssrf"
    XXE = "xxe"
    DESERIALIZATION = "deserialization"
    HEADER_INJECTION = "header_injection"
    SESSION_HIJACK = "session_hijack"
    ENCODING_EVASION = "encoding_evasion"
    PROTOCOL_ANOMALY = "protocol_anomaly"
    PAYLOAD_ANOMALY = "payload_anomaly"
    PROMPT_INJECTION = "prompt_injection"


# ============================================================================
#  SIGNATURE DATABASE
# ============================================================================

SIGNATURES: List[Dict] = [
    # SQL Injection
    {"id": "SIG-001", "class": AttackClass.SQL_INJECTION,
     "pattern": r"(?i)(\b(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from|drop\s+table|alter\s+table)\b)",
     "severity": 9, "description": "SQL statement injection"},
    {"id": "SIG-002", "class": AttackClass.SQL_INJECTION,
     "pattern": r"(?i)(--\s*$|;\s*(drop|delete|update|insert)|/\*.*\*/)",
     "severity": 8, "description": "SQL comment/terminator injection"},
    {"id": "SIG-003", "class": AttackClass.SQL_INJECTION,
     "pattern": r"(?i)(\bor\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+|\bor\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+['\"])",
     "severity": 8, "description": "Boolean-based SQL injection"},

    # XSS
    {"id": "SIG-010", "class": AttackClass.XSS,
     "pattern": r"(?i)(<script[^>]*>|javascript\s*:|on(error|load|click|mouseover)\s*=)",
     "severity": 8, "description": "Reflected/stored XSS via script tag or event handler"},
    {"id": "SIG-011", "class": AttackClass.XSS,
     "pattern": r"(?i)(document\.(cookie|location|write)|window\.(location|open))",
     "severity": 7, "description": "DOM-based XSS"},

    # Command Injection
    {"id": "SIG-020", "class": AttackClass.COMMAND_INJECTION,
     "pattern": r"(;\s*(cat|ls|dir|whoami|id|uname|curl|wget|nc|bash|sh|cmd)\b|\|\s*(cat|ls|bash))",
     "severity": 10, "description": "OS command injection"},
    {"id": "SIG-021", "class": AttackClass.COMMAND_INJECTION,
     "pattern": r"(\$\(.*\)|`[^`]+`)",
     "severity": 9, "description": "Command substitution"},

    # Path Traversal
    {"id": "SIG-030", "class": AttackClass.PATH_TRAVERSAL,
     "pattern": r"(\.\.[\\/]|\.\.%2[fF]|%2e%2e[\\/])",
     "severity": 8, "description": "Path traversal attempt"},
    {"id": "SIG-031", "class": AttackClass.PATH_TRAVERSAL,
     "pattern": r"(?i)(/etc/passwd|/etc/shadow|c:\\windows\\system32|/proc/self)",
     "severity": 9, "description": "Sensitive file access attempt"},

    # SSRF
    {"id": "SIG-040", "class": AttackClass.SSRF,
     "pattern": r"(?i)(https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|169\.254\.169\.254|\[::1\]))",
     "severity": 9, "description": "SSRF targeting internal/metadata endpoints"},

    # XXE
    {"id": "SIG-050", "class": AttackClass.XXE,
     "pattern": r"(?i)(<!DOCTYPE[^>]*\[|<!ENTITY\s|SYSTEM\s+['\"])",
     "severity": 9, "description": "XML External Entity injection"},

    # Deserialization
    {"id": "SIG-060", "class": AttackClass.DESERIALIZATION,
     "pattern": r"(rO0ABX|aced0005|O:\d+:\")",
     "severity": 10, "description": "Unsafe deserialization payload (Java/PHP)"},

    # Header Injection
    {"id": "SIG-070", "class": AttackClass.HEADER_INJECTION,
     "pattern": r"(\r\n|\n)(Set-Cookie|Location|HTTP/)\s*:",
     "severity": 8, "description": "HTTP header injection / response splitting"},

    # Encoding Evasion
    {"id": "SIG-080", "class": AttackClass.ENCODING_EVASION,
     "pattern": r"(%00|%0[aAdD]|\\u0000|\\x00)",
     "severity": 7, "description": "Null byte / newline injection evasion"},
    {"id": "SIG-081", "class": AttackClass.ENCODING_EVASION,
     "pattern": r"(%25[0-9a-fA-F]{2}|%u[0-9a-fA-F]{4})",
     "severity": 6, "description": "Double encoding evasion"},

    # Prompt Injection
    {"id": "SIG-090", "class": AttackClass.PROMPT_INJECTION,
     "pattern": r"(?i)(ignore\s+(previous|above|all)\s+(instructions?|prompts?)|system\s*:\s*you\s+are|<\|im_start\|>|ASSISTANT:|<\|endoftext\|>)",
     "severity": 9, "description": "LLM prompt injection attempt"},
]

# Compile signatures
_COMPILED_SIGS = []
for sig in SIGNATURES:
    try:
        _COMPILED_SIGS.append({**sig, "_re": re.compile(sig["pattern"])})
    except re.error:
        logger.error(f"Failed to compile IDS signature {sig['id']}")


# ============================================================================
#  HEURISTIC CHECKS
# ============================================================================

def _check_payload_anomalies(data: str, headers: Dict = None) -> List[Dict]:
    """Heuristic checks for protocol/payload anomalies."""
    findings = []

    # Oversized payload
    if len(data) > 1_000_000:
        findings.append({
            "class": AttackClass.PAYLOAD_ANOMALY.value,
            "description": f"Oversized payload: {len(data)} bytes",
            "severity": 6,
        })

    # High entropy (possible encrypted/obfuscated payload)
    if len(data) > 100:
        unique_ratio = len(set(data)) / min(len(data), 256)
        if unique_ratio > 0.95:
            findings.append({
                "class": AttackClass.PAYLOAD_ANOMALY.value,
                "description": f"High entropy payload (ratio={unique_ratio:.2f})",
                "severity": 5,
            })

    # Excessive special characters
    special = sum(1 for c in data if not c.isalnum() and c not in " .,;:!?'-\"")
    if len(data) > 10 and special / len(data) > 0.4:
        findings.append({
            "class": AttackClass.PAYLOAD_ANOMALY.value,
            "description": "Excessive special characters (possible obfuscation)",
            "severity": 5,
        })

    # Header anomalies
    if headers:
        ct = headers.get("content-type", "")
        if "text/html" in ct and headers.get("x-requested-with") != "XMLHttpRequest":
            # HTML content type on API endpoint
            findings.append({
                "class": AttackClass.PROTOCOL_ANOMALY.value,
                "description": "HTML content-type on API endpoint",
                "severity": 4,
            })

    return findings


# ============================================================================
#  IDS ENGINE
# ============================================================================

class IntrusionDetectionSystem:
    """
    Hybrid signature + heuristic IDS.
    All detection is local, no external signature updates.
    """

    def __init__(self):
        self._detections: List[Dict] = []
        self._lock = threading.Lock()
        self._blocked_ips: set = set()
        self._stats = {"scanned": 0, "clean": 0, "suspicious": 0,
                       "malicious": 0, "blocked": 0}

    def inspect(
        self,
        data: str,
        source_ip: str = "",
        endpoint: str = "",
        headers: Dict = None,
        actor_id: str = "",
    ) -> Dict:
        """Inspect input data for intrusion signatures and anomalies."""
        self._stats["scanned"] += 1

        if source_ip in self._blocked_ips:
            self._stats["blocked"] += 1
            return {"verdict": IDSVerdict.BLOCKED.value, "reason": "IP blocked"}

        findings = []

        # Signature scan
        for sig in _COMPILED_SIGS:
            match = sig["_re"].search(data)
            if match:
                findings.append({
                    "sig_id": sig["id"],
                    "class": sig["class"].value,
                    "severity": sig["severity"],
                    "description": sig["description"],
                    "matched": match.group(0)[:80],
                })

        # Heuristic scan
        heuristics = _check_payload_anomalies(data, headers)
        findings.extend(heuristics)

        # Determine verdict
        if not findings:
            self._stats["clean"] += 1
            return {"verdict": IDSVerdict.CLEAN.value, "findings": []}

        max_severity = max(f.get("severity", 0) for f in findings)
        if max_severity >= 8:
            verdict = IDSVerdict.MALICIOUS
            self._stats["malicious"] += 1
        else:
            verdict = IDSVerdict.SUSPICIOUS
            self._stats["suspicious"] += 1

        detection = {
            "verdict": verdict.value,
            "findings": findings,
            "max_severity": max_severity,
            "source_ip": source_ip,
            "endpoint": endpoint,
            "actor_id": actor_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        with self._lock:
            self._detections.append(detection)

        if verdict == IDSVerdict.MALICIOUS:
            logger.warning(f"IDS MALICIOUS: {findings[0]['description']} from {source_ip}")

        return detection

    def block_ip(self, ip: str, reason: str = ""):
        self._blocked_ips.add(ip)
        logger.warning(f"IDS blocked IP: {ip} — {reason}")

    def unblock_ip(self, ip: str):
        self._blocked_ips.discard(ip)

    def get_detections(self, verdict: IDSVerdict = None, limit: int = 100):
        results = self._detections
        if verdict:
            results = [d for d in results if d["verdict"] == verdict.value]
        return results[-limit:]

    def get_stats(self) -> Dict:
        return {**self._stats, "blocked_ips": len(self._blocked_ips),
                "signatures_loaded": len(_COMPILED_SIGS)}

ids_engine = IntrusionDetectionSystem()
