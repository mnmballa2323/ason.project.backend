"""
Code Guardian — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Simulates a Coding Agent (CodeAson / Ason2.5-Coder) that strictly 
enforces Infrastructure-as-Code (IaC) security best practices.

Scans Terraform files in `infra/` for:
- Open Security Groups (0.0.0.0/0)
- Unencrypted Resources
- Hardcoded Secrets
"""
import logging
import os
import re
from typing import List, Dict, Any

from services.memory import memory_engine
from services.self_healing import self_healing

logger = logging.getLogger("qwen.code_guardian")

class CodeGuardian:
    """
    The Static Analysis Sentinel.
    """
    
    INFRA_ROOT = "c:\\Users\\hyper\\Desktop\\workspace\\ason.project\\infra"
    
    SUSPICIOUS_PATTERNS = [
        (r'cidr_blocks\s*=\s*\["0.0.0.0/0"\]', "CRITICAL: Open Security Group found (0.0.0.0/0)"),
        (r'encrypted\s*=\s*false', "HIGH: Unencrypted Resource detected"),
        (r'password\s*=\s*".+"', "HIGH: Hardcoded password detected"),
        (r'access_key\s*=\s*".+"', "CRITICAL: Hardcoded Access Key detected"),
        (r'http://', "MEDIUM: Insecure HTTP protocol usage")
    ]

    def scan_codebase(self) -> Dict[str, Any]:
        """
        Walk the infra directory and analyze .tf files.
        """
        findings = []
        files_scanned = 0
        
        if not os.path.exists(self.INFRA_ROOT):
            return {"status": "error", "message": "Infra directory not found"}

        for root, _, files in os.walk(self.INFRA_ROOT):
            for file in files:
                if file.endswith(".tf"):
                    files_scanned += 1
                    path = os.path.join(root, file)
                    self._analyze_file(path, findings)
        
        score = 100 - (len(findings) * 5)
        score = max(0, score)
        
        result = {
            "agent": "CodeAson (Simulated)",
            "files_scanned": files_scanned,
            "security_score": score,
            "findings": findings[:10], # Top 10
            "status": "SECURE" if score >= 90 else "VULNERABLE"
        }
        
        if findings:
            logger.warning(f"🛡️ Code Guardian found {len(findings)} issues.")
            # 1. Memorize the Security Risk
            for finding in findings:
                 memory_engine.add_memory(
                    f"Security Vulnerability: {finding}",
                    tags=["security", "iac", "terraform"]
                )
            # 2. Trigger Self-Healing (Lockdown)
            if score < 80:
                self_healing.trigger_remediation("infra-repo", "Security Policy Violation")
        else:
            logger.info("🛡️ Code Guardian: Infrastructure is clean.")
            
        return result

    def _analyze_file(self, path: str, findings: List[str]):
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                
            for pattern, msg in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, content):
                    rel_path = os.path.relpath(path, self.INFRA_ROOT)
                    findings.append(f"{msg} in {rel_path}")
                    
        except Exception as e:
            logger.error(f"Failed to analyze {path}: {e}")

code_guardian = CodeGuardian()
