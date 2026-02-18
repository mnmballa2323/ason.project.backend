"""
Vulnerability Scanner — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Dependency audit, CVE tracking, and configuration
vulnerability scanning. All checks are local — no
external vulnerability databases or scanning services.
"""

import hashlib
import json
import logging
import re
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.vuln_scanner")


class VulnSeverity(str, Enum):
    CRITICAL = "critical"     # CVSS 9.0-10.0
    HIGH = "high"             # CVSS 7.0-8.9
    MEDIUM = "medium"         # CVSS 4.0-6.9
    LOW = "low"               # CVSS 0.1-3.9
    INFORMATIONAL = "info"


class VulnCategory(str, Enum):
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    ENCRYPTION = "encryption"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INPUT_VALIDATION = "input_validation"
    SECRETS = "secrets"
    NETWORK = "network"
    LOGGING = "logging"
    CONTAINER = "container"


class VulnStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"      # Risk accepted with justification
    FALSE_POSITIVE = "false_positive"


class Vulnerability:
    """A discovered vulnerability."""
    def __init__(self, vuln_id, title, severity, category,
                 description, remediation, component=""):
        self.vuln_id = vuln_id
        self.title = title
        self.severity = severity
        self.category = category
        self.description = description
        self.remediation = remediation
        self.component = component
        self.status = VulnStatus.OPEN
        self.discovered_at = datetime.now(timezone.utc).isoformat()
        self.remediated_at: Optional[str] = None
        self.cvss_score: Optional[float] = None
        self.cve_id: Optional[str] = None

    def mitigate(self, notes=""):
        self.status = VulnStatus.MITIGATED
        self.remediated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "vuln_id": self.vuln_id, "title": self.title,
            "severity": self.severity.value, "category": self.category.value,
            "status": self.status.value, "component": self.component,
            "description": self.description, "remediation": self.remediation,
            "cvss_score": self.cvss_score, "discovered_at": self.discovered_at,
        }


# ============================================================================
#  SECURITY CHECKS
# ============================================================================

# Known-vulnerable dependency patterns (local signature database)
KNOWN_VULN_DEPS = [
    {"pattern": r"pyyaml[<= ]*(5\.\d)", "cve": "CVE-2020-14343",
     "title": "PyYAML unsafe load", "severity": VulnSeverity.CRITICAL,
     "remediation": "Upgrade to PyYAML >= 6.0, use safe_load()"},
    {"pattern": r"requests[<= ]*(2\.1[0-9]\.\d)", "cve": "CVE-2023-32681",
     "title": "Requests unintended header leak", "severity": VulnSeverity.MEDIUM,
     "remediation": "Upgrade to requests >= 2.31.0"},
    {"pattern": r"cryptography[<= ]*(3\d?\.\d)", "cve": "CVE-2023-49083",
     "title": "Cryptography NULL dereference", "severity": VulnSeverity.HIGH,
     "remediation": "Upgrade to cryptography >= 41.0.6"},
    {"pattern": r"urllib3[<= ]*(1\.\d+\.\d+)", "cve": "CVE-2023-45803",
     "title": "urllib3 request body leak", "severity": VulnSeverity.MEDIUM,
     "remediation": "Upgrade to urllib3 >= 2.0.7"},
    {"pattern": r"jinja2[<= ]*(2\.\d+)", "cve": "CVE-2024-22195",
     "title": "Jinja2 XSS via xmlattr filter", "severity": VulnSeverity.MEDIUM,
     "remediation": "Upgrade to Jinja2 >= 3.1.3"},
    {"pattern": r"pillow[<= ]*(9\.\d)", "cve": "CVE-2023-50447",
     "title": "Pillow arbitrary code execution", "severity": VulnSeverity.CRITICAL,
     "remediation": "Upgrade to Pillow >= 10.2.0"},
]

# Configuration security checks
CONFIG_CHECKS = [
    {"check_id": "CFG-001", "title": "Debug mode in production",
     "check": lambda cfg: cfg.get("debug", False) or cfg.get("DEBUG", False),
     "severity": VulnSeverity.HIGH, "category": VulnCategory.CONFIGURATION,
     "remediation": "Disable debug mode (set DEBUG=false)"},
    {"check_id": "CFG-002", "title": "Default credentials present",
     "check": lambda cfg: any(v in str(cfg.values()) for v in ["password", "admin", "changeme", "123456"]),
     "severity": VulnSeverity.CRITICAL, "category": VulnCategory.SECRETS,
     "remediation": "Replace all default credentials with strong, unique values"},
    {"check_id": "CFG-003", "title": "TLS version below 1.2",
     "check": lambda cfg: cfg.get("tls_version", "1.3") in ("1.0", "1.1"),
     "severity": VulnSeverity.HIGH, "category": VulnCategory.ENCRYPTION,
     "remediation": "Enforce TLS 1.2+ minimum"},
    {"check_id": "CFG-004", "title": "CORS wildcard enabled",
     "check": lambda cfg: cfg.get("cors_origin", "") == "*",
     "severity": VulnSeverity.MEDIUM, "category": VulnCategory.NETWORK,
     "remediation": "Restrict CORS origins to specific domains"},
    {"check_id": "CFG-005", "title": "Audit logging disabled",
     "check": lambda cfg: not cfg.get("audit_enabled", True),
     "severity": VulnSeverity.HIGH, "category": VulnCategory.LOGGING,
     "remediation": "Enable audit logging for compliance"},
    {"check_id": "CFG-006", "title": "Rate limiting disabled",
     "check": lambda cfg: not cfg.get("rate_limit_enabled", True),
     "severity": VulnSeverity.MEDIUM, "category": VulnCategory.NETWORK,
     "remediation": "Enable rate limiting to prevent abuse"},
    {"check_id": "CFG-007", "title": "Session timeout exceeds 30 minutes",
     "check": lambda cfg: cfg.get("session_timeout_minutes", 30) > 30,
     "severity": VulnSeverity.LOW, "category": VulnCategory.AUTHENTICATION,
     "remediation": "Set session timeout to ≤30 minutes"},
    {"check_id": "CFG-008", "title": "Encryption at rest disabled",
     "check": lambda cfg: not cfg.get("encryption_at_rest", True),
     "severity": VulnSeverity.CRITICAL, "category": VulnCategory.ENCRYPTION,
     "remediation": "Enable AES-256-GCM encryption at rest"},
]


class VulnerabilityScanner:
    """Local vulnerability scanner — no external feeds."""

    def __init__(self):
        self._vulns: Dict[str, Vulnerability] = {}
        self._lock = threading.Lock()
        self._counter = 0

    def scan_dependencies(self, requirements_text: str) -> List[Vulnerability]:
        """Scan a requirements.txt-style string for known vulnerabilities."""
        findings = []
        for dep_sig in KNOWN_VULN_DEPS:
            match = re.search(dep_sig["pattern"], requirements_text, re.IGNORECASE)
            if match:
                vuln = self._create_vuln(
                    dep_sig["title"], dep_sig["severity"],
                    VulnCategory.DEPENDENCY,
                    f"Vulnerable version: {match.group(0)}",
                    dep_sig["remediation"],
                    match.group(0),
                )
                vuln.cve_id = dep_sig.get("cve")
                findings.append(vuln)
        return findings

    def scan_configuration(self, config: Dict) -> List[Vulnerability]:
        """Scan configuration for security issues."""
        findings = []
        for check in CONFIG_CHECKS:
            try:
                if check["check"](config):
                    vuln = self._create_vuln(
                        check["title"], check["severity"],
                        check["category"],
                        check["title"],
                        check["remediation"],
                        check["check_id"],
                    )
                    findings.append(vuln)
            except Exception:
                pass
        return findings

    def scan_secrets_in_code(self, code: str) -> List[Vulnerability]:
        """Detect hardcoded secrets in source code."""
        patterns = [
            (r'(?i)(password|passwd|secret|api_key|apikey|token)\s*=\s*["\'][^"\']{8,}["\']',
             "Hardcoded secret detected", VulnSeverity.CRITICAL),
            (r'(?i)(BEGIN\s+(RSA|DSA|EC)\s+PRIVATE\s+KEY)',
             "Private key in source code", VulnSeverity.CRITICAL),
            (r'(?i)aws_secret_access_key\s*=\s*["\'][A-Za-z0-9/+=]{40}["\']',
             "AWS secret key in code", VulnSeverity.CRITICAL),
            (r'ghp_[A-Za-z0-9]{36}', "GitHub personal access token", VulnSeverity.HIGH),
            (r'sk-[A-Za-z0-9]{32,}', "API key (sk- prefix) in code", VulnSeverity.HIGH),
        ]
        findings = []
        for pattern, title, severity in patterns:
            if re.search(pattern, code):
                findings.append(self._create_vuln(
                    title, severity, VulnCategory.SECRETS,
                    title, "Remove hardcoded secrets; use environment variables or secret manager",
                ))
        return findings

    def _create_vuln(self, title, severity, category, description,
                     remediation, component="") -> Vulnerability:
        with self._lock:
            self._counter += 1
            vuln_id = f"VULN-{self._counter:06d}"
        vuln = Vulnerability(vuln_id, title, severity, category,
                             description, remediation, component)
        self._vulns[vuln_id] = vuln
        return vuln

    def get_report(self) -> Dict:
        open_vulns = [v for v in self._vulns.values() if v.status == VulnStatus.OPEN]
        by_severity = {}
        for v in open_vulns:
            by_severity[v.severity.value] = by_severity.get(v.severity.value, 0) + 1
        return {
            "total": len(self._vulns),
            "open": len(open_vulns),
            "by_severity": by_severity,
            "critical_count": by_severity.get("critical", 0),
            "vulnerabilities": [v.to_dict() for v in open_vulns],
        }

vuln_scanner = VulnerabilityScanner()
