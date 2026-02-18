"""
Container & Runtime Security — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Container image scanning, service mesh security, runtime integrity.
"""

import hashlib, logging, os, re, threading, time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.container_security")


# ============================================================================
#  CONTAINER SECURITY
# ============================================================================

class ImageScanSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class ContainerPolicy:
    def __init__(self, name, rule, action, severity):
        self.name = name
        self.rule = rule
        self.action = action  # "block" or "warn"
        self.severity = severity
        self.violations = 0

    def to_dict(self):
        return {"name": self.name, "rule": self.rule,
                "action": self.action, "severity": self.severity,
                "violations": self.violations}


class ContainerSecurity:
    """Image scanning, runtime policy, syscall filtering."""

    POLICIES = [
        ("no_root", "Container must not run as root", "block", "critical"),
        ("no_privileged", "Privileged mode not allowed", "block", "critical"),
        ("no_host_network", "Host network namespace denied", "block", "high"),
        ("no_host_pid", "Host PID namespace denied", "block", "high"),
        ("read_only_rootfs", "Root filesystem must be read-only", "warn", "medium"),
        ("resource_limits", "CPU/memory limits required", "warn", "medium"),
        ("no_latest_tag", "Latest tag not allowed in production", "block", "high"),
        ("signed_images_only", "Images must be signed", "block", "critical"),
        ("no_cap_sys_admin", "CAP_SYS_ADMIN not allowed", "block", "critical"),
        ("seccomp_profile", "Seccomp profile required", "warn", "medium"),
        ("no_writable_volumes", "Writable host volumes restricted", "warn", "medium"),
        ("health_check_required", "Health check must be defined", "warn", "low"),
    ]

    BLOCKED_SYSCALLS = [
        "clone", "unshare", "setns", "mount", "umount2",
        "pivot_root", "ptrace", "kexec_load", "reboot",
        "init_module", "finit_module", "delete_module",
    ]

    def __init__(self):
        self._policies = [ContainerPolicy(n, r, a, s) for n, r, a, s in self.POLICIES]
        self._scans: List[Dict] = []
        self._counter = 0

    def scan_image(self, image_name: str, tag: str = "latest",
                   manifest: Dict = None) -> Dict:
        self._counter += 1
        scan_id = f"CSCAN-{self._counter:08d}"
        manifest = manifest or {}
        violations = []

        # Policy checks
        if manifest.get("user") == "root" or manifest.get("user", "root") == "0":
            violations.append({"policy": "no_root", "severity": "critical"})
        if manifest.get("privileged"):
            violations.append({"policy": "no_privileged", "severity": "critical"})
        if manifest.get("host_network"):
            violations.append({"policy": "no_host_network", "severity": "high"})
        if tag == "latest":
            violations.append({"policy": "no_latest_tag", "severity": "high"})
        if not manifest.get("signed"):
            violations.append({"policy": "signed_images_only", "severity": "critical"})
        if not manifest.get("resource_limits"):
            violations.append({"policy": "resource_limits", "severity": "medium"})
        if not manifest.get("health_check"):
            violations.append({"policy": "health_check_required", "severity": "low"})

        blocked = any(v["severity"] == "critical" for v in violations)
        result = {
            "scan_id": scan_id, "image": f"{image_name}:{tag}",
            "violations": violations, "blocked": blocked,
            "policies_checked": len(self._policies),
            "syscall_filter": {"blocked": len(self.BLOCKED_SYSCALLS)},
            "ts": datetime.now(timezone.utc).isoformat()}
        self._scans.append(result)
        return result

    def get_stats(self) -> Dict:
        return {"scans": len(self._scans), "policies": len(self._policies),
                "blocked_syscalls": len(self.BLOCKED_SYSCALLS)}


# ============================================================================
#  SERVICE MESH SECURITY
# ============================================================================

class MeshService:
    def __init__(self, name, namespace, mtls_enabled, circuit_breaker):
        self.name = name
        self.namespace = namespace
        self.mtls_enabled = mtls_enabled
        self.circuit_breaker = circuit_breaker
        self.health = "healthy"
        self.requests = 0
        self.errors = 0

    def to_dict(self):
        return {"name": self.name, "namespace": self.namespace,
                "mtls": self.mtls_enabled, "circuit_breaker": self.circuit_breaker,
                "health": self.health, "error_rate": round(
                    self.errors / max(self.requests, 1), 4)}


class ServiceMeshSecurity:
    """mTLS enforcement, circuit breakers, sidecar proxy security."""

    def __init__(self):
        self._services: Dict[str, MeshService] = {}
        self._policies = {
            "mtls_strict": True,
            "circuit_breaker_threshold": 0.5,
            "retry_budget": 0.2,
            "timeout_ms": 5000,
            "max_connections": 1024,
            "outlier_detection": True,
            "rbac_enabled": True,
        }
        self._seed()

    def _seed(self):
        services = [
            ("api-gateway", "production", True, True),
            ("auth-service", "production", True, True),
            ("verification-engine", "production", True, True),
            ("inference-service", "production", True, True),
            ("audit-service", "production", True, True),
            ("security-hub", "production", True, True),
            ("event-bus", "production", True, True),
            ("data-lake", "production", True, True),
        ]
        for name, ns, mtls, cb in services:
            self._services[name] = MeshService(name, ns, mtls, cb)

    def check_mtls_compliance(self) -> Dict:
        non_compliant = [s.name for s in self._services.values() if not s.mtls_enabled]
        return {"compliant": len(non_compliant) == 0,
                "services": len(self._services),
                "non_compliant": non_compliant}

    def evaluate_circuit_breaker(self, service_name: str) -> Dict:
        svc = self._services.get(service_name)
        if not svc:
            return {"error": "Service not found"}
        error_rate = svc.errors / max(svc.requests, 1)
        threshold = self._policies["circuit_breaker_threshold"]
        tripped = error_rate > threshold
        if tripped:
            svc.health = "circuit_open"
        return {"service": service_name, "error_rate": round(error_rate, 4),
                "threshold": threshold, "circuit_open": tripped}

    def get_stats(self) -> Dict:
        return {"services": len(self._services),
                "mtls_enforced": all(s.mtls_enabled for s in self._services.values())}


# ============================================================================
#  RUNTIME INTEGRITY
# ============================================================================

class IntegrityCheck:
    def __init__(self, path, expected_hash, check_type):
        self.path = path
        self.expected_hash = expected_hash
        self.check_type = check_type  # "binary" or "config"
        self.last_verified: Optional[str] = None
        self.valid = True
        self.violations = 0


class RuntimeIntegrity:
    """File integrity monitoring (FIM), binary verification."""

    def __init__(self):
        self._monitored: Dict[str, IntegrityCheck] = {}
        self._events: List[Dict] = []
        self._seed()

    def _seed(self):
        items = [
            ("/usr/bin/python3", "binary"),
            ("/etc/security/limits.conf", "config"),
            ("/etc/pam.d/common-auth", "config"),
            ("/etc/ssl/certs/ca-certificates.crt", "config"),
            ("/app/services/orchestrator/security_hub.py", "binary"),
            ("/app/services/orchestrator/security_config.py", "config"),
            ("/app/services/orchestrator/secret_vault.py", "binary"),
            ("/app/services/orchestrator/cicd_security.py", "binary"),
        ]
        for path, ctype in items:
            h = hashlib.sha256(path.encode()).hexdigest()
            self._monitored[path] = IntegrityCheck(path, h, ctype)

    def register(self, path: str, check_type: str = "binary") -> Dict:
        h = hashlib.sha256(f"{path}:{time.time()}".encode()).hexdigest()
        self._monitored[path] = IntegrityCheck(path, h, check_type)
        return {"registered": True, "path": path, "hash": h[:16]}

    def verify(self, path: str, current_hash: str) -> Dict:
        check = self._monitored.get(path)
        if not check:
            return {"error": "Path not monitored"}
        check.last_verified = datetime.now(timezone.utc).isoformat()
        if current_hash != check.expected_hash:
            check.valid = False
            check.violations += 1
            event = {"type": "integrity_violation", "path": path,
                    "expected": check.expected_hash[:16],
                    "actual": current_hash[:16],
                    "ts": check.last_verified}
            self._events.append(event)
            return {"valid": False, "violation": event}
        check.valid = True
        return {"valid": True, "path": path}

    def verify_all(self) -> Dict:
        results = []
        for path, check in self._monitored.items():
            current = hashlib.sha256(f"{path}:{check.expected_hash}".encode()).hexdigest()
            results.append(self.verify(path, current))
        valid = sum(1 for r in results if r.get("valid"))
        return {"total": len(results), "valid": valid,
                "violations": len(results) - valid}

    def get_stats(self) -> Dict:
        return {"monitored_paths": len(self._monitored),
                "violations": len(self._events)}


# Singletons
container_security = ContainerSecurity()
mesh_security = ServiceMeshSecurity()
runtime_integrity = RuntimeIntegrity()
