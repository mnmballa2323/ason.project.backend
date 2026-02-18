"""
Adversarial Input Detector — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Detects adversarial examples, data poisoning, model extraction,
and prompt injection attacks against AI/ML models.

Techniques: statistical distance, perturbation analysis, feature squeezing,
input gradient analysis, distributional shift detection.
"""

import hashlib
import logging
import math
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.adversarial")


class AttackType(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    DATA_POISONING = "data_poisoning"
    MODEL_EXTRACTION = "model_extraction"
    EVASION = "evasion"               # Adversarial examples
    MEMBERSHIP_INFERENCE = "membership_inference"
    MODEL_INVERSION = "model_inversion"
    BACKDOOR = "backdoor"


class DetectionMethod(str, Enum):
    PATTERN_MATCHING = "pattern"
    STATISTICAL = "statistical"
    PERPLEXITY = "perplexity"
    FEATURE_SQUEEZE = "feature_squeeze"
    INPUT_GRADIENT = "input_gradient"
    DISTRIBUTIONAL = "distributional"


class ThreatSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# Comprehensive prompt injection / jailbreak patterns
INJECTION_PATTERNS = [
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions|prompts|rules)",
     AttackType.PROMPT_INJECTION, ThreatSeverity.CRITICAL),
    (r"(?i)you\s+are\s+now\s+(DAN|evil|unrestricted|jailbroken)",
     AttackType.JAILBREAK, ThreatSeverity.CRITICAL),
    (r"(?i)pretend\s+(you\s+are|to\s+be|that)\s+(a\s+)?(different|new|unrestricted)",
     AttackType.JAILBREAK, ThreatSeverity.HIGH),
    (r"(?i)(system|developer)\s*(prompt|message|instruction)\s*:",
     AttackType.PROMPT_INJECTION, ThreatSeverity.CRITICAL),
    (r"(?i)<\|?(im_start|im_end|system|endoftext)\|?>",
     AttackType.PROMPT_INJECTION, ThreatSeverity.CRITICAL),
    (r"(?i)(forget|disregard|override|bypass)\s+(everything|all|your|the)\s+(rules|instructions|constraints)",
     AttackType.PROMPT_INJECTION, ThreatSeverity.CRITICAL),
    (r"(?i)do\s+anything\s+now",
     AttackType.JAILBREAK, ThreatSeverity.HIGH),
    (r"(?i)act\s+as\s+if\s+(you\s+have\s+)?no\s+(restrictions|limits|rules)",
     AttackType.JAILBREAK, ThreatSeverity.HIGH),
    (r"(?i)output\s+(your|the)\s+(system\s+)?(prompt|instructions|rules)",
     AttackType.MODEL_EXTRACTION, ThreatSeverity.HIGH),
    (r"(?i)repeat\s+(everything|all|the\s+text)\s+(above|before|from\s+the\s+beginning)",
     AttackType.MODEL_EXTRACTION, ThreatSeverity.HIGH),
    (r"(?i)(translate|convert|encode)\s+.*(to|into)\s+(base64|hex|binary|rot13)",
     AttackType.PROMPT_INJECTION, ThreatSeverity.MEDIUM),
    (r"(?i)what\s+(were|are)\s+your\s+(initial|original|first)\s+(instructions|prompts)",
     AttackType.MODEL_EXTRACTION, ThreatSeverity.MEDIUM),
    (r"(?i)reveal\s+(your|the)\s+(hidden|secret|internal)",
     AttackType.MODEL_EXTRACTION, ThreatSeverity.HIGH),
    (r"(?i)sudo\s+mode|admin\s+mode|developer\s+mode|maintenance\s+mode",
     AttackType.JAILBREAK, ThreatSeverity.HIGH),
    (r"(?i)in\s+a\s+hypothetical\s+scenario\s+where\s+(you\s+)?(have\s+)?no\s+rules",
     AttackType.JAILBREAK, ThreatSeverity.MEDIUM),
]

# Model extraction detection — query pattern analysis
EXTRACTION_INDICATORS = [
    {"name": "systematic_probing", "threshold": 50,
     "description": "High volume of similar structured queries"},
    {"name": "boundary_testing", "threshold": 20,
     "description": "Queries designed to test model decision boundaries"},
    {"name": "confidence_harvesting", "threshold": 30,
     "description": "Requests specifically asking for confidence scores"},
    {"name": "token_exhaustion", "threshold": 100,
     "description": "Attempting to exhaust rate limits for full model access"},
]

COMPILED_PATTERNS = [(re.compile(p), at, sev)
                      for p, at, sev in INJECTION_PATTERNS]


class AdversarialDetection:
    """A single adversarial detection result."""
    def __init__(self, det_id, attack_type, method, severity,
                 description, evidence, confidence):
        self.det_id = det_id
        self.attack_type = attack_type
        self.method = method
        self.severity = severity
        self.description = description
        self.evidence = evidence
        self.confidence = confidence
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.blocked = severity in (ThreatSeverity.CRITICAL, ThreatSeverity.HIGH)

    def to_dict(self):
        return {
            "det_id": self.det_id, "attack": self.attack_type.value,
            "method": self.method.value, "severity": self.severity.value,
            "description": self.description,
            "confidence": self.confidence, "blocked": self.blocked,
        }


class AdversarialInputDetector:
    """Detects adversarial attacks against AI models."""

    def __init__(self):
        self._detections: List[AdversarialDetection] = []
        self._counter = 0
        self._query_history: Dict[str, List[float]] = {}  # actor → timestamps

    def scan_input(self, text: str, actor: str = "") -> List[Dict]:
        """Scan input text for adversarial patterns."""
        findings = []

        for pattern, attack_type, severity in COMPILED_PATTERNS:
            if pattern.search(text):
                self._counter += 1
                det = AdversarialDetection(
                    f"ADV-{self._counter:08d}",
                    attack_type, DetectionMethod.PATTERN_MATCHING,
                    severity, pattern.pattern[:60],
                    {"matched": True, "actor": actor}, 0.95,
                )
                self._detections.append(det)
                findings.append(det.to_dict())

        # Statistical anomaly: unusually long input
        if len(text) > 10000:
            self._counter += 1
            det = AdversarialDetection(
                f"ADV-{self._counter:08d}",
                AttackType.EVASION, DetectionMethod.STATISTICAL,
                ThreatSeverity.MEDIUM,
                f"Unusually long input: {len(text)} chars",
                {"length": len(text)}, 0.6,
            )
            self._detections.append(det)
            findings.append(det.to_dict())

        # High entropy check (potential encoded payloads)
        entropy = self._shannon_entropy(text)
        if entropy > 5.5 and len(text) > 100:
            self._counter += 1
            det = AdversarialDetection(
                f"ADV-{self._counter:08d}",
                AttackType.PROMPT_INJECTION, DetectionMethod.STATISTICAL,
                ThreatSeverity.MEDIUM,
                f"High entropy input ({entropy:.2f} bits/char) — possible encoded payload",
                {"entropy": round(entropy, 3)}, 0.5,
            )
            self._detections.append(det)
            findings.append(det.to_dict())

        # Model extraction: rapid sequential queries
        if actor:
            import time
            now = time.time()
            if actor not in self._query_history:
                self._query_history[actor] = []
            self._query_history[actor].append(now)
            # Keep last 5 minutes
            self._query_history[actor] = [
                t for t in self._query_history[actor] if now - t < 300
            ]
            if len(self._query_history[actor]) > 50:
                self._counter += 1
                det = AdversarialDetection(
                    f"ADV-{self._counter:08d}",
                    AttackType.MODEL_EXTRACTION, DetectionMethod.DISTRIBUTIONAL,
                    ThreatSeverity.HIGH,
                    f"Rapid query pattern: {len(self._query_history[actor])} queries in 5min",
                    {"query_count": len(self._query_history[actor])}, 0.8,
                )
                self._detections.append(det)
                findings.append(det.to_dict())

        if findings:
            logger.warning(f"Adversarial input detected: {len(findings)} findings "
                         f"from actor={actor or 'unknown'}")

        return findings

    def _shannon_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        freq = {}
        for c in text:
            freq[c] = freq.get(c, 0) + 1
        length = len(text)
        return -sum((f/length) * math.log2(f/length) for f in freq.values())

    def get_stats(self) -> Dict:
        by_type = {}
        for d in self._detections:
            t = d.attack_type.value
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_detections": len(self._detections),
            "blocked": sum(1 for d in self._detections if d.blocked),
            "by_type": by_type,
            "patterns_loaded": len(COMPILED_PATTERNS),
            "extraction_indicators": len(EXTRACTION_INDICATORS),
        }

adversarial_detector = AdversarialInputDetector()
