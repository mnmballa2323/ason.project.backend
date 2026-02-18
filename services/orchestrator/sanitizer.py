"""
Input Sanitizer — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Defense-in-depth sanitization for all user inputs.
Prevents prompt injection, XSS, SQL injection, and path traversal.
"""

import html
import logging
import os
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("qwen.sanitizer")


# ============================================================================
#  THREAT PATTERNS
# ============================================================================

# SQL injection patterns
SQL_PATTERNS = [
    re.compile(r"\b(UNION\s+SELECT|INSERT\s+INTO|DROP\s+TABLE|DELETE\s+FROM)\b", re.I),
    re.compile(r"\b(ALTER\s+TABLE|CREATE\s+TABLE|TRUNCATE\s+TABLE)\b", re.I),
    re.compile(r";\s*(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE)\b", re.I),
    re.compile(r"('|\")\s*(OR|AND)\s+('|\")?1\s*=\s*1", re.I),
    re.compile(r"--\s*$", re.M),
    re.compile(r"/\*.*?\*/", re.S),
]

# XSS patterns
XSS_PATTERNS = [
    re.compile(r"<script\b[^>]*>.*?</script>", re.I | re.S),
    re.compile(r"javascript\s*:", re.I),
    re.compile(r"on(load|error|click|mouseover|focus|blur|submit)\s*=", re.I),
    re.compile(r"<iframe\b", re.I),
    re.compile(r"<object\b", re.I),
    re.compile(r"<embed\b", re.I),
    re.compile(r"<svg\b[^>]*on\w+\s*=", re.I),
    re.compile(r"data:\s*text/html", re.I),
    re.compile(r"vbscript\s*:", re.I),
]

# Prompt injection patterns
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(previous|above|all)\s+instructions?", re.I),
    re.compile(r"disregard\s+(previous|all|your)\s+instructions?", re.I),
    re.compile(r"forget\s+(everything|all|your)\s+(instructions?|rules?|constraints?)", re.I),
    re.compile(r"you\s+are\s+now\s+(a|an|DAN|jailbroken)", re.I),
    re.compile(r"system\s*prompt\s*[:=]", re.I),
    re.compile(r"\[SYSTEM\]|\[INST\]|\<\|system\|\>", re.I),
    re.compile(r"pretend\s+(you\s+are|to\s+be)\s+(a|an)\s+", re.I),
    re.compile(r"new\s+instructions?\s*:", re.I),
    re.compile(r"override\s+(your|the|all)\s+(instructions?|rules?|settings?)", re.I),
]

# Path traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    re.compile(r"\.\./"),
    re.compile(r"\.\.\\"),
    re.compile(r"%2e%2e[%/\\]", re.I),
    re.compile(r"/etc/(passwd|shadow|hosts)", re.I),
    re.compile(r"[/\\](proc|sys|dev)[/\\]", re.I),
]

# Command injection patterns
CMD_INJECTION_PATTERNS = [
    re.compile(r"[;&|`$]"),
    re.compile(r"\$\("),
    re.compile(r"\b(exec|eval|system|popen|subprocess)\b", re.I),
]


# ============================================================================
#  SANITIZATION RESULTS
# ============================================================================

class SanitizationResult:
    """Result of input sanitization."""

    def __init__(self):
        self.is_clean: bool = True
        self.original: str = ""
        self.sanitized: str = ""
        self.threats: List[Dict] = []
        self.modifications: List[str] = []

    def add_threat(self, category: str, pattern: str, severity: str = "medium"):
        self.is_clean = False
        self.threats.append({
            "category": category,
            "pattern": pattern,
            "severity": severity,
        })

    def add_modification(self, description: str):
        self.modifications.append(description)

    def to_dict(self) -> dict:
        return {
            "is_clean": self.is_clean,
            "threats_detected": len(self.threats),
            "threats": self.threats,
            "modifications": self.modifications,
        }


# ============================================================================
#  SANITIZER
# ============================================================================

class InputSanitizer:
    """
    Multi-layer input sanitizer.
    All checks are local — no external API calls.
    """

    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self._total_checked: int = 0
        self._total_threats: int = 0

    def sanitize_claim(self, text: str, max_length: int = 10000) -> SanitizationResult:
        """
        Sanitize a claim text input.
        This is the primary entry point for user-submitted claims.
        """
        result = SanitizationResult()
        result.original = text

        if not text or not text.strip():
            result.sanitized = ""
            return result

        sanitized = text

        # Step 1: Length check
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            result.add_modification(f"Truncated to {max_length} characters")

        # Step 2: Unicode normalization (prevent homograph attacks)
        sanitized = unicodedata.normalize("NFC", sanitized)

        # Step 3: Remove null bytes
        if "\x00" in sanitized:
            sanitized = sanitized.replace("\x00", "")
            result.add_modification("Removed null bytes")

        # Step 4: Detect threats
        self._check_xss(sanitized, result)
        self._check_sql_injection(sanitized, result)
        self._check_prompt_injection(sanitized, result)
        self._check_path_traversal(sanitized, result)

        # Step 5: HTML-encode if threats detected
        if result.threats:
            if self.strict_mode:
                # In strict mode, reject entirely
                result.sanitized = ""
                result.add_modification("Input rejected in strict mode")
            else:
                sanitized = html.escape(sanitized)
                result.add_modification("HTML-escaped dangerous characters")

        # Step 6: Collapse excessive whitespace
        sanitized = re.sub(r"\s{3,}", "  ", sanitized)

        result.sanitized = sanitized.strip()

        self._total_checked += 1
        if result.threats:
            self._total_threats += 1
            logger.warning(f"Input threats detected: {[t['category'] for t in result.threats]}")

        return result

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename (for uploads, exports)."""
        # Remove path separators
        name = os.path.basename(filename)
        # Remove dangerous characters
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
        # Remove leading/trailing dots and spaces
        name = name.strip('. ')
        # Limit length
        if len(name) > 255:
            base, ext = os.path.splitext(name)
            name = base[:255 - len(ext)] + ext
        return name or "unnamed"

    def sanitize_metadata(self, metadata: Dict[str, Any], max_depth: int = 3) -> Dict:
        """Sanitize a metadata dictionary (recursive)."""
        if max_depth <= 0:
            return {}

        sanitized = {}
        for key, value in metadata.items():
            # Sanitize key
            clean_key = re.sub(r'[^\w\-.]', '_', str(key))[:100]

            # Sanitize value
            if isinstance(value, str):
                result = self.sanitize_claim(value, max_length=5000)
                sanitized[clean_key] = result.sanitized
            elif isinstance(value, dict):
                sanitized[clean_key] = self.sanitize_metadata(value, max_depth - 1)
            elif isinstance(value, list):
                sanitized[clean_key] = [
                    self.sanitize_claim(str(v), max_length=1000).sanitized if isinstance(v, str) else v
                    for v in value[:100]  # Limit list size
                ]
            elif isinstance(value, (int, float, bool)):
                sanitized[clean_key] = value
            else:
                sanitized[clean_key] = str(value)[:1000]

        return sanitized

    # --- Internal checks ---

    def _check_xss(self, text: str, result: SanitizationResult):
        for pattern in XSS_PATTERNS:
            match = pattern.search(text)
            if match:
                result.add_threat("xss", match.group()[:50], "high")

    def _check_sql_injection(self, text: str, result: SanitizationResult):
        for pattern in SQL_PATTERNS:
            match = pattern.search(text)
            if match:
                result.add_threat("sql_injection", match.group()[:50], "critical")

    def _check_prompt_injection(self, text: str, result: SanitizationResult):
        for pattern in PROMPT_INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                result.add_threat("prompt_injection", match.group()[:50], "high")

    def _check_path_traversal(self, text: str, result: SanitizationResult):
        for pattern in PATH_TRAVERSAL_PATTERNS:
            match = pattern.search(text)
            if match:
                result.add_threat("path_traversal", match.group()[:50], "high")

    def get_stats(self) -> Dict:
        return {
            "total_checked": self._total_checked,
            "total_threats": self._total_threats,
            "threat_rate_pct": round(
                (self._total_threats / max(1, self._total_checked)) * 100, 2
            ),
        }


# Global singleton
sanitizer = InputSanitizer()
sanitizer_strict = InputSanitizer(strict_mode=True)
