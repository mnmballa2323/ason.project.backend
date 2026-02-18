"""
Security Config — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Centralized configuration for all security modules.
Enable/disable, thresholds, severity tuning, feature flags.
"""

import logging, copy
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("qwen.security_config")


class SecurityLevel(str, Enum):
    MAXIMUM = "maximum"       # All features, strictest thresholds
    HIGH = "high"             # Production recommended
    STANDARD = "standard"     # Balanced security/performance
    DEVELOPMENT = "development"  # Relaxed for dev environments


DEFAULT_CONFIG = {
    "global": {
        "security_level": SecurityLevel.HIGH.value,
        "zero_api": True,
        "air_gap_capable": True,
        "telemetry": False,      # ALWAYS FALSE — zero telemetry
        "external_calls": False, # ALWAYS FALSE — zero external APIs
    },

    "modules": {
        "post_quantum":       {"enabled": True, "default_algo": "ML-KEM-768"},
        "crypto_agility":     {"enabled": True, "blocked_algos": ["MD5", "SHA1", "DES"]},
        "hsm":                {"enabled": True, "fips_level": 3},
        "apt_detector":       {"enabled": True, "min_confidence": 0.7},
        "deception":          {"enabled": True, "assets": 15},
        "threat_hunting":     {"enabled": True, "hunt_interval_hours": 4},
        "sbom":               {"enabled": True, "format": "cyclonedx"},
        "code_signing":       {"enabled": True, "algo": "ECDSA-P384"},
        "dep_integrity":      {"enabled": True, "typosquat_threshold": 2},
        "secure_build":       {"enabled": True, "slsa_level": 3},
        "soar":               {"enabled": True, "auto_mode": True, "sla_minutes": 15},
        "containment":        {"enabled": True, "auto_escalate": True, "max_level": "lockdown"},
        "threat_fusion":      {"enabled": True, "sources": 10},
        "security_chaos":     {"enabled": True, "auto_run": False},
        "zkp":                {"enabled": True, "default_system": "PLONK"},
        "fhe":                {"enabled": True, "default_scheme": "BFV"},
        "differential_privacy": {"enabled": True, "max_epsilon": 1.0},
        "mpc":                {"enabled": True, "default_protocol": "shamir"},
        "adversarial":        {"enabled": True, "auto_block": True},
        "watermark":          {"enabled": True},
        "ai_redteam":         {"enabled": True, "categories": 8},
        "model_drift":        {"enabled": True, "check_interval_hours": 1},
        "eu_ai_act":          {"enabled": True, "default_risk": "limited"},
        "data_sovereignty":   {"enabled": True, "default_jurisdiction": "US"},
        "cross_border":       {"enabled": True},
        "identity":           {"enabled": True, "passwordless": True, "mfa_required": True},
        "resilience":         {"enabled": True, "regions": 5},
        "governance":         {"enabled": True},
        "network_defense":    {"enabled": True, "rasp_mode": "block"},
        "forensics":          {"enabled": True, "auto_seal": True},
        "perf_security":      {"enabled": True, "hw_accel": True},
        "offensive":          {"enabled": True, "cart_enabled": True},
        "quantum_safe":       {"enabled": True, "qkd_protocol": "BB84"},
        "formal_methods":     {"enabled": True, "verify_on_deploy": True},
        "ctip":               {"enabled": True, "ioc_ttl_days": 90},
        "dlp":                {"enabled": True, "action_on_restricted": "block"},
        "ispm":               {"enabled": True, "cspm_rules": 10, "kspm_checks": 10},
        "privacy":            {"enabled": True, "dsar_deadline_days": 30},
        "secmlops":           {"enabled": True, "bias_threshold": 0.80},
        "blockchain":         {"enabled": True, "merkle_backed": True},
        "edge_security":      {"enabled": True, "tpm_required": True},
        "maturity":           {"enabled": True, "target_cmmc": "level_2"},
    },

    "thresholds": {
        "rate_limit_per_minute": 100,
        "max_failed_logins": 5,
        "session_timeout_minutes": 30,
        "password_min_length": 14,
        "mfa_grace_period_seconds": 0,
        "key_rotation_days": 90,
        "cert_expiry_warning_days": 30,
        "audit_retention_days": 2555,  # 7 years
        "backup_retention_days": 365,
        "vulnerability_patch_hours": 24,
        "incident_sla_minutes": 15,
    },

    "hardcoded_security": {
        "_NOTICE": "These values CANNOT be changed — hardcoded for security",
        "telemetry_enabled": False,
        "external_api_calls": False,
        "backdoors": False,
        "tracking": False,
        "phone_home": False,
        "third_party_analytics": False,
    }
}

# Security levels preset overrides
LEVEL_OVERRIDES = {
    SecurityLevel.MAXIMUM: {
        "thresholds.rate_limit_per_minute": 50,
        "thresholds.max_failed_logins": 3,
        "thresholds.session_timeout_minutes": 15,
        "thresholds.password_min_length": 20,
        "thresholds.vulnerability_patch_hours": 4,
        "thresholds.incident_sla_minutes": 5,
    },
    SecurityLevel.DEVELOPMENT: {
        "thresholds.rate_limit_per_minute": 1000,
        "thresholds.max_failed_logins": 50,
        "thresholds.session_timeout_minutes": 480,
        "thresholds.password_min_length": 8,
        "thresholds.vulnerability_patch_hours": 168,
    },
}


class SecurityConfig:
    """Centralized security configuration management."""

    def __init__(self):
        self._config = copy.deepcopy(DEFAULT_CONFIG)
        self._change_log: List[Dict] = []

    def get(self, path: str, default: Any = None) -> Any:
        """Get config value by dot-path, e.g. 'modules.soar.auto_mode'"""
        parts = path.split(".")
        current = self._config
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        return current

    def set(self, path: str, value: Any) -> Dict:
        """Set a config value. Blocked for hardcoded_security items."""
        if path.startswith("hardcoded_security"):
            return {"error": "Hardcoded security values cannot be changed",
                    "blocked": True}
        # Block any attempt to enable telemetry/tracking
        if any(kw in path.lower() for kw in ("telemetry", "tracking", "phone_home",
                                               "backdoor", "analytics", "external_call")):
            if value in (True, "true", 1):
                return {"error": "Security policy: cannot enable telemetry/tracking",
                        "blocked": True}

        parts = path.split(".")
        current = self._config
        for part in parts[:-1]:
            if part in current:
                current = current[part]
            else:
                return {"error": f"Path not found: {path}"}
        old = current.get(parts[-1])
        current[parts[-1]] = value
        change = {"path": path, "old": old, "new": value,
                  "ts": datetime.now(timezone.utc).isoformat()}
        self._change_log.append(change)
        return change

    def is_module_enabled(self, module_name: str) -> bool:
        return self.get(f"modules.{module_name}.enabled", False)

    def apply_security_level(self, level: SecurityLevel) -> Dict:
        """Apply a security level preset."""
        self._config["global"]["security_level"] = level.value
        overrides = LEVEL_OVERRIDES.get(level, {})
        applied = []
        for path, value in overrides.items():
            result = self.set(path, value)
            if "error" not in result:
                applied.append(result)
        return {"level": level.value, "overrides_applied": len(applied)}

    def export_config(self) -> Dict:
        return copy.deepcopy(self._config)

    def get_change_log(self) -> List[Dict]:
        return self._change_log[-50:]

    def get_stats(self) -> Dict:
        enabled = sum(1 for m in self._config.get("modules", {}).values()
                      if m.get("enabled", False))
        return {
            "security_level": self._config["global"]["security_level"],
            "modules_enabled": enabled,
            "modules_total": len(self._config.get("modules", {})),
            "config_changes": len(self._change_log),
            "telemetry": False,  # ALWAYS FALSE
            "external_apis": False,  # ALWAYS FALSE
        }


security_config = SecurityConfig()
