"""
Vulnerability Management Platform — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

CVE scanning, CVSS scoring, patch orchestration, exploit prediction.
"""

import hashlib, logging, math, os, threading, time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.vuln_mgmt")


# ============================================================================
#  VULNERABILITY SCANNER
# ============================================================================

class CVSSSeverity(str, Enum):
    CRITICAL = "critical"  # CVSS 9.0-10.0
    HIGH = "high"          # CVSS 7.0-8.9
    MEDIUM = "medium"      # CVSS 4.0-6.9
    LOW = "low"            # CVSS 0.1-3.9
    NONE = "none"          # CVSS 0.0


class Vulnerability:
    def __init__(self, cve_id, title, cvss, severity, package,
                 affected_versions, fixed_version, description):
        self.cve_id = cve_id
        self.title = title
        self.cvss = cvss
        self.severity = severity
        self.package = package
        self.affected_versions = affected_versions
        self.fixed_version = fixed_version
        self.description = description
        self.discovered_at = datetime.now(timezone.utc).isoformat()
        self.status = "open"  # open, patched, mitigated, accepted
        self.epss_score = 0.0

    def to_dict(self):
        return {"cve": self.cve_id, "cvss": self.cvss,
                "severity": self.severity.value, "package": self.package,
                "fixed": self.fixed_version, "status": self.status,
                "epss": self.epss_score}


class VulnerabilityScanner:
    """CVE database matching with CVSS v3.1 scoring."""

    def __init__(self):
        self._cve_db: Dict[str, Vulnerability] = {}
        self._scan_results: List[Dict] = []
        self._counter = 0
        self._seed()

    def _seed(self):
        vulns = [
            ("CVE-2024-3094", "XZ Utils Backdoor", 10.0, CVSSSeverity.CRITICAL,
             "xz-utils", ["5.6.0", "5.6.1"], "5.6.2", "Supply chain backdoor in xz-utils"),
            ("CVE-2023-44487", "HTTP/2 Rapid Reset", 7.5, CVSSSeverity.HIGH,
             "http2", ["*"], "patched", "HTTP/2 rapid reset DDoS"),
            ("CVE-2023-38545", "curl SOCKS5 heap overflow", 9.8, CVSSSeverity.CRITICAL,
             "curl", ["<8.4.0"], "8.4.0", "SOCKS5 proxy heap buffer overflow"),
            ("CVE-2023-4863", "libwebp heap overflow", 8.8, CVSSSeverity.HIGH,
             "libwebp", ["<1.3.2"], "1.3.2", "WebP image processing heap overflow"),
            ("CVE-2024-21626", "runc container escape", 8.6, CVSSSeverity.HIGH,
             "runc", ["<1.1.12"], "1.1.12", "Container escape via WORKDIR"),
            ("CVE-2023-32233", "Linux kernel nftables UAF", 7.8, CVSSSeverity.HIGH,
             "linux-kernel", ["<6.4"], "6.4", "nf_tables use-after-free"),
            ("CVE-2024-0204", "GoAnywhere MFT auth bypass", 9.8, CVSSSeverity.CRITICAL,
             "goanywhere", ["<7.4.1"], "7.4.1", "Authentication bypass"),
            ("CVE-2023-46747", "F5 BIG-IP auth bypass", 9.8, CVSSSeverity.CRITICAL,
             "big-ip", ["<17.1.1"], "17.1.1", "Unauthenticated remote code execution"),
        ]
        for cve, title, cvss, sev, pkg, affected, fixed, desc in vulns:
            self._cve_db[cve] = Vulnerability(cve, title, cvss, sev, pkg,
                                              affected, fixed, desc)

    def scan(self, packages: List[Dict] = None) -> Dict:
        self._counter += 1
        scan_id = f"VSCAN-{self._counter:08d}"
        packages = packages or []
        findings = []
        for pkg_info in packages:
            pkg_name = pkg_info.get("name", "")
            pkg_version = pkg_info.get("version", "")
            for vuln in self._cve_db.values():
                if vuln.package == pkg_name:
                    findings.append(vuln.to_dict())
        result = {
            "scan_id": scan_id, "packages_scanned": len(packages),
            "vulnerabilities": len(findings),
            "critical": sum(1 for f in findings if f["severity"] == "critical"),
            "high": sum(1 for f in findings if f["severity"] == "high"),
            "findings": findings,
            "ts": datetime.now(timezone.utc).isoformat()}
        self._scan_results.append(result)
        return result

    def get_cve(self, cve_id: str) -> Dict:
        vuln = self._cve_db.get(cve_id)
        return vuln.to_dict() if vuln else {"error": "CVE not found"}

    def get_stats(self) -> Dict:
        return {"cves_in_db": len(self._cve_db), "scans": len(self._scan_results)}


# ============================================================================
#  PATCH ORCHESTRATOR
# ============================================================================

class PatchStatus(str, Enum):
    PENDING = "pending"
    TESTING = "testing"
    CANARY = "canary"
    ROLLING = "rolling"
    COMPLETE = "complete"
    ROLLBACK = "rollback"


class PatchJob:
    def __init__(self, job_id, cve_id, package, target_version, strategy):
        self.job_id = job_id
        self.cve_id = cve_id
        self.package = package
        self.target_version = target_version
        self.strategy = strategy
        self.status = PatchStatus.PENDING
        self.steps: List[str] = []
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None

    def to_dict(self):
        return {"id": self.job_id, "cve": self.cve_id,
                "package": self.package, "target": self.target_version,
                "strategy": self.strategy, "status": self.status.value,
                "steps": len(self.steps)}


class PatchOrchestrator:
    """Automated patching with rollback and canary deployment."""

    def __init__(self):
        self._jobs: Dict[str, PatchJob] = {}
        self._counter = 0

    def create_patch(self, cve_id: str, package: str, target_version: str,
                    strategy: str = "canary") -> Dict:
        self._counter += 1
        jid = f"PATCH-{self._counter:08d}"
        job = PatchJob(jid, cve_id, package, target_version, strategy)
        self._jobs[jid] = job

        if strategy == "canary":
            job.steps = [
                "snapshot_current_state",
                "deploy_canary_10pct",
                "monitor_canary_15min",
                "expand_to_25pct",
                "monitor_25pct_15min",
                "full_rollout",
                "verify_patch",
                "cleanup_old_version",
            ]
        elif strategy == "rolling":
            job.steps = [
                "snapshot_current_state",
                "rolling_update_batch_1",
                "health_check_batch_1",
                "rolling_update_batch_2",
                "health_check_batch_2",
                "verify_patch",
            ]
        else:  # immediate
            job.steps = [
                "snapshot_current_state",
                "apply_patch",
                "verify_patch",
            ]
        return job.to_dict()

    def execute(self, job_id: str) -> Dict:
        job = self._jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        # Simulate execution
        for step in job.steps:
            job.status = PatchStatus.ROLLING
        job.status = PatchStatus.COMPLETE
        job.completed_at = datetime.now(timezone.utc)
        return {"completed": True, **job.to_dict()}

    def rollback(self, job_id: str) -> Dict:
        job = self._jobs.get(job_id)
        if not job:
            return {"error": "Job not found"}
        job.status = PatchStatus.ROLLBACK
        return {"rolled_back": True, **job.to_dict()}

    def get_stats(self) -> Dict:
        return {"jobs": len(self._jobs),
                "completed": sum(1 for j in self._jobs.values()
                                if j.status == PatchStatus.COMPLETE)}


# ============================================================================
#  EXPLOIT PREDICTION (EPSS-style)
# ============================================================================

class ExploitPrediction:
    """EPSS-style exploit probability scoring for prioritization."""

    FACTORS = {
        "public_exploit": 0.35,
        "weaponized": 0.25,
        "network_vector": 0.10,
        "no_auth_required": 0.10,
        "low_complexity": 0.08,
        "high_impact": 0.07,
        "active_campaigns": 0.05,
    }

    def __init__(self):
        self._scores: Dict[str, Dict] = {}

    def predict(self, cve_id: str, factors: Dict[str, bool] = None) -> Dict:
        factors = factors or {}
        score = 0.0
        contributing = []
        for factor, weight in self.FACTORS.items():
            if factors.get(factor, False):
                score += weight
                contributing.append(factor)
        # CVSS influence
        cvss = factors.get("cvss", 5.0)
        if isinstance(cvss, (int, float)):
            score += (cvss / 10.0) * 0.15

        score = min(1.0, score)
        priority = ("critical" if score > 0.7 else
                   "high" if score > 0.4 else
                   "medium" if score > 0.2 else "low")
        result = {
            "cve": cve_id, "epss_score": round(score, 4),
            "priority": priority, "contributing_factors": contributing,
            "recommendation": (
                "Patch immediately" if priority == "critical" else
                "Patch within 24h" if priority == "high" else
                "Patch within 7 days" if priority == "medium" else
                "Schedule for next cycle")}
        self._scores[cve_id] = result
        return result

    def get_stats(self) -> Dict:
        return {"cves_scored": len(self._scores)}


# Singletons
vuln_scanner = VulnerabilityScanner()
patch_orchestrator = PatchOrchestrator()
exploit_predictor = ExploitPrediction()
