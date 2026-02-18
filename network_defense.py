"""
Advanced Network Defense — Ason Verification Platform
ZERO EXTERNAL APIs

RASP, DNS security, API schema enforcement, JA3/JA4 fingerprinting.
"""

import hashlib, logging, re, time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.network_defense")


class RASPAction(str, Enum):
    BLOCK = "block"
    LOG = "log"
    SANITIZE = "sanitize"
    CHALLENGE = "challenge"


class DNSThreatType(str, Enum):
    DGA = "dga_domain"
    TUNNELING = "dns_tunneling"
    TYPOSQUAT = "typosquat"
    MALWARE_C2 = "malware_c2"
    PHISHING = "phishing"


RASP_RULES = [
    ("SQL Injection", r"(?i)(union\s+select|;\s*drop\s|or\s+1\s*=\s*1|'\s*or\s*')", RASPAction.BLOCK),
    ("XSS", r"<script[^>]*>|javascript:|on\w+\s*=", RASPAction.BLOCK),
    ("Path Traversal", r"\.\./|\.\.\\|%2e%2e", RASPAction.BLOCK),
    ("Command Injection", r";\s*(ls|cat|rm|wget|curl)\s|`[^`]+`|\$\(", RASPAction.BLOCK),
    ("SSRF", r"(?i)(127\.0\.0\.1|localhost|0\.0\.0\.0|169\.254\.\d+\.\d+|10\.\d+|172\.(1[6-9]|2|3[01]))", RASPAction.BLOCK),
    ("XXE", r"<!ENTITY|<!DOCTYPE.*\[|SYSTEM\s+[\"']", RASPAction.BLOCK),
    ("LDAP Injection", r"[)(|*\\].*=.*[)(|*\\]", RASPAction.LOG),
    ("Log Injection", r"[\r\n].*(?:INFO|WARN|ERROR|DEBUG)", RASPAction.SANITIZE),
    ("Header Injection", r"[\r\n]\s*(Set-Cookie|Location):", RASPAction.BLOCK),
    ("Prototype Pollution", r"__proto__|constructor\s*\[|Object\.assign", RASPAction.BLOCK),
]

DGA_INDICATORS = [
    lambda d: len(d) > 20,  # Unusually long
    lambda d: sum(c.isdigit() for c in d) / max(1, len(d)) > 0.3,  # High digit ratio
    lambda d: len(set(d)) / max(1, len(d)) > 0.8,  # High entropy chars
]

COMPILED_RASP = [(name, re.compile(pat), action) for name, pat, action in RASP_RULES]


class RASPDetection:
    def __init__(self, det_id, rule, action, payload_snippet):
        self.det_id = det_id
        self.rule = rule
        self.action = action
        self.snippet = payload_snippet[:100]
        self.ts = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {"id": self.det_id, "rule": self.rule,
                "action": self.action.value, "snippet": self.snippet}


class JA3Fingerprint:
    def __init__(self, fp_hash, client_hello_info, known_client=""):
        self.hash = fp_hash
        self.info = client_hello_info
        self.known = known_client
        self.seen_count = 1
        self.first_seen = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {"hash": self.hash[:16], "known": self.known or "unknown",
                "seen": self.seen_count}


KNOWN_JA3 = {
    "e7d705a3286e19ea42f587b344ee6865": "Chrome/120",
    "b32309a26951912be7dba376398abc3b": "Firefox/121",
    "0535884bcab6004e6fd65084a45f8e25": "curl/8.x",
    "a0e9f5d64349fb13f4f1bacf0b2c820b": "Python-requests",
    "cd08e31494f9531f560d64c695473da9": "Cobalt Strike",
    "72a589da586844d7f0818ce684948eea": "Metasploit",
    "3b5074b1b5d032e5620f69f9f700ff0e": "Mimikatz",
}


class NetworkDefenseEngine:
    """Advanced network security layer."""

    def __init__(self):
        self._rasp_detections: List[RASPDetection] = []
        self._dns_blocks: List[Dict] = []
        self._ja3_db: Dict[str, JA3Fingerprint] = {}
        self._counter = 0
        for h, c in KNOWN_JA3.items():
            self._ja3_db[h] = JA3Fingerprint(h, {}, c)

    def rasp_scan(self, input_data: str, context: str = "") -> List[Dict]:
        findings = []
        for name, pattern, action in COMPILED_RASP:
            if pattern.search(input_data):
                self._counter += 1
                det = RASPDetection(f"RASP-{self._counter:08d}",
                                    name, action, input_data)
                self._rasp_detections.append(det)
                findings.append(det.to_dict())
        return findings

    def check_dns(self, domain: str) -> Dict:
        threat = None
        for check in DGA_INDICATORS:
            if check(domain):
                threat = DNSThreatType.DGA
                break
        if threat:
            record = {"domain": domain, "threat": threat.value,
                      "action": "sinkholed",
                      "ts": datetime.now(timezone.utc).isoformat()}
            self._dns_blocks.append(record)
            return record
        return {"domain": domain, "threat": None, "action": "allowed"}

    def classify_ja3(self, ja3_hash: str) -> Dict:
        fp = self._ja3_db.get(ja3_hash)
        if fp:
            fp.seen_count += 1
            malicious = fp.known in ("Cobalt Strike", "Metasploit", "Mimikatz")
            return {"hash": ja3_hash[:16], "known": fp.known,
                    "malicious": malicious, "action": "block" if malicious else "allow"}
        self._ja3_db[ja3_hash] = JA3Fingerprint(ja3_hash, {})
        return {"hash": ja3_hash[:16], "known": "unknown", "malicious": False}

    def validate_api_schema(self, method: str, path: str,
                            body: Dict, schema: Dict) -> Dict:
        errors = []
        required = schema.get("required", [])
        for field in required:
            if field not in body:
                errors.append(f"Missing required field: {field}")
        props = schema.get("properties", {})
        for key, value in body.items():
            if key not in props:
                errors.append(f"Unexpected field: {key}")
        return {"valid": len(errors) == 0, "errors": errors,
                "method": method, "path": path}

    def get_stats(self) -> Dict:
        return {
            "rasp_detections": len(self._rasp_detections),
            "rasp_rules": len(COMPILED_RASP),
            "dns_blocks": len(self._dns_blocks),
            "ja3_fingerprints": len(self._ja3_db),
            "known_malicious_ja3": sum(1 for f in self._ja3_db.values()
                                       if f.known in ("Cobalt Strike", "Metasploit", "Mimikatz")),
        }

network_defense = NetworkDefenseEngine()
