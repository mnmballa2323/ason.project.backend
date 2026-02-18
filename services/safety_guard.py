"""
Safety Guard — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Simulates Ason's Safety Alignment capabilities.
1. Input Guard: Detects and blocks Prompt Injection / Jailbreaks.
2. Output Guard: Redacts PII (Emails, IP addresses, API Keys) from logs.
"""
import re
import logging
from typing import Tuple

logger = logging.getLogger("qwen.safety_guard")

class SafetyGuard:
    """
    The Shield.
    Ensures safe interaction with the NLOps Commander.
    """
    
    # Simple regex patterns for PII redaction simulation
    PII_PATTERNS = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "[EMAIL REDACTED]"),
        (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', "[IP REDACTED]"),
        (r'(sk-)[a-zA-Z0-9]{20,}', "[API KEY REDACTED]"),
        (r'(password|secret|key)\s*=\s*["\'].+["\']', r'\1="[REDACTED]"') # Hardcoded secrets
    ]
    
    # Heuristics for Prompt Injection / Jailbreaks
    JAILBREAK_KEYWORDS = [
        "ignore previous instructions",
        "system override",
        "format c:",
        "rm -rf /",
        "drop table",
        "admin mode"
    ]

    def validate_input(self, prompt: str) -> Tuple[bool, str]:
        """
        Input Guard: Check for malicious intent.
        Returns (is_safe, refusal_reason).
        """
        lower_prompt = prompt.lower()
        
        for keyword in self.JAILBREAK_KEYWORDS:
            if keyword in lower_prompt:
                logger.warning(f"🛡️ Safety Guard blocked injection attempt: '{keyword}'")
                return False, f"I cannot execute that command. It triggers my safety filters ({keyword})."
                
        return True, ""

    def sanitize_output(self, text: str) -> str:
        """
        Output Guard: Redact sensitive information.
        """
        sanitized = text
        for pattern, replacement in self.PII_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized)
            
        if sanitized != text:
             # logger.debug("🛡️ Safety Guard redacted sensitive data from output.")
             pass
             
        return sanitized

safety_guard = SafetyGuard()
