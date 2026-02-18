"""
Security Digital Twin — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Infrastructure simulation, what-if analysis, attack simulation.
"""

import hashlib, logging, os, threading, time, copy
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.digital_twin")


# ============================================================================
#  DIGITAL TWIN
# ============================================================================

class ComponentStatus(str, Enum):
    RUNNING = "running"
    DEGRADED = "degraded"
    DOWN = "down"
    MAINTENANCE = "maintenance"


class TwinComponent:
    def __init__(self, name, comp_type, region, criticality,
                 dependencies=None, config=None):
        self.name = name
        self.comp_type = comp_type  # service, database, network, identity
        self.region = region
        self.criticality = criticality  # 1-10
        self.dependencies = dependencies or []
        self.config = config or {}
        self.status = ComponentStatus.RUNNING
        self.risk_score = 0.0
        self.patches_pending = 0
        self.mfa_enabled = True
        self.encrypted = True
        self.last_backup = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "name": self.name, "type": self.comp_type,
            "region": self.region, "criticality": self.criticality,
            "status": self.status.value, "risk_score": self.risk_score,
            "dependencies": self.dependencies,
            "mfa": self.mfa_enabled, "encrypted": self.encrypted}


class DigitalTwin:
    """Mirror your entire infra as a simulation."""

    def __init__(self):
        self._components: Dict[str, TwinComponent] = {}
        self._snapshots: List[Dict] = []
        self._seed()

    def _seed(self):
        components = [
            ("api-gateway", "service", "us-east-1", 10,
             [], {"tls": "1.3", "rate_limit": 100}),
            ("auth-service", "service", "us-east-1", 10,
             ["api-gateway", "pg-primary", "redis"], {"mfa": "required"}),
            ("verification-engine", "service", "us-east-1", 9,
             ["auth-service", "pg-primary", "object-store"], {}),
            ("security-hub", "service", "us-east-1", 10,
             ["event-bus", "data-lake"], {}),
            ("event-bus", "service", "us-east-1", 9, [], {}),
            ("data-lake", "service", "us-east-1", 8,
             ["pg-primary"], {}),
            ("pg-primary", "database", "us-east-1", 10,
             [], {"encryption": "AES-256", "replication": "sync"}),
            ("pg-replica", "database", "us-west-2", 8,
             ["pg-primary"], {"read_only": True}),
            ("redis", "database", "us-east-1", 7,
             [], {"maxmemory": "4gb"}),
            ("object-store", "storage", "us-east-1", 8,
             [], {"encryption": "AES-256-GCM"}),
            ("load-balancer", "network", "us-east-1", 10,
             [], {"waf": True}),
            ("vpn-gateway", "network", "us-east-1", 8,
             [], {"protocol": "WireGuard"}),
            ("dns", "network", "global", 10, [], {"dnssec": True}),
            ("admin-users", "identity", "global", 9,
             [], {"count": 5, "mfa": "hardware"}),
            ("service-accounts", "identity", "global", 7,
             [], {"count": 12, "rotation": "90d"}),
            ("tls-certs", "certificate", "global", 9,
             [], {"expiry": "2027-01-01", "issuer": "internal-ca"}),
        ]
        for name, ctype, region, crit, deps, config in components:
            self._components[name] = TwinComponent(name, ctype, region, crit, deps, config)

    def snapshot(self) -> Dict:
        snap = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "components": {k: v.to_dict() for k, v in self._components.items()},
            "total": len(self._components),
            "healthy": sum(1 for c in self._components.values()
                          if c.status == ComponentStatus.RUNNING),
        }
        self._snapshots.append(snap)
        return snap

    def get_component(self, name: str) -> Dict:
        comp = self._components.get(name)
        return comp.to_dict() if comp else {"error": "Not found"}

    def update_component(self, name: str, **kwargs) -> Dict:
        comp = self._components.get(name)
        if not comp:
            return {"error": "Not found"}
        for k, v in kwargs.items():
            if hasattr(comp, k):
                setattr(comp, k, v)
        return comp.to_dict()

    def clone(self) -> "DigitalTwin":
        """Deep clone for what-if analysis."""
        twin = DigitalTwin.__new__(DigitalTwin)
        twin._components = {k: copy.deepcopy(v) for k, v in self._components.items()}
        twin._snapshots = []
        return twin

    def get_stats(self) -> Dict:
        return {"components": len(self._components),
                "snapshots": len(self._snapshots)}


# ============================================================================
#  WHAT-IF ENGINE
# ============================================================================

class WhatIfScenario:
    def __init__(self, name, description, changes):
        self.name = name
        self.description = description
        self.changes = changes  # List of {component, field, new_value}

    def to_dict(self):
        return {"name": self.name, "description": self.description,
                "changes": len(self.changes)}


class WhatIfEngine:
    """'What if we disable MFA?' — instant blast radius + risk delta."""

    def __init__(self, twin: DigitalTwin):
        self._twin = twin
        self._analyses: List[Dict] = []

    def analyze(self, scenario_name: str, changes: List[Dict]) -> Dict:
        """Apply changes to a clone and compute impact."""
        # Snapshot baseline
        baseline = self._compute_risk(self._twin)

        # Clone and apply changes
        clone = self._twin.clone()
        applied = []
        for change in changes:
            comp = clone._components.get(change.get("component"))
            if comp:
                field = change.get("field")
                new_val = change.get("value")
                old_val = getattr(comp, field, None) if hasattr(comp, field) else comp.config.get(field)
                if hasattr(comp, field):
                    setattr(comp, field, new_val)
                else:
                    comp.config[field] = new_val
                applied.append({"component": comp.name, "field": field,
                              "old": str(old_val), "new": str(new_val)})

        # Compute new risk
        modified = self._compute_risk(clone)
        delta = modified["total_risk"] - baseline["total_risk"]

        # Cascade analysis
        affected = self._cascade_impact(clone, [c["component"] for c in changes])

        result = {
            "scenario": scenario_name,
            "changes_applied": applied,
            "baseline_risk": baseline["total_risk"],
            "modified_risk": modified["total_risk"],
            "risk_delta": round(delta, 2),
            "risk_direction": "increase" if delta > 0 else "decrease" if delta < 0 else "neutral",
            "affected_components": affected,
            "recommendation": "REJECT" if delta > 10 else "REVIEW" if delta > 0 else "APPROVE",
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._analyses.append(result)
        return result

    def _compute_risk(self, twin: DigitalTwin) -> Dict:
        total = 0
        for comp in twin._components.values():
            risk = comp.criticality * 5
            if not comp.mfa_enabled:
                risk += 25
            if not comp.encrypted:
                risk += 20
            if comp.status != ComponentStatus.RUNNING:
                risk += 15
            if comp.patches_pending > 0:
                risk += comp.patches_pending * 5
            comp.risk_score = risk
            total += risk
        return {"total_risk": round(total, 2)}

    def _cascade_impact(self, twin: DigitalTwin, changed: List[str]) -> List[str]:
        affected = set(changed)
        for comp in twin._components.values():
            if any(dep in changed for dep in comp.dependencies):
                affected.add(comp.name)
        return list(affected)

    # Pre-built scenarios
    def what_if_disable_mfa(self) -> Dict:
        return self.analyze("Disable MFA", [
            {"component": "auth-service", "field": "mfa_enabled", "value": False},
            {"component": "admin-users", "field": "mfa_enabled", "value": False},
        ])

    def what_if_disable_encryption(self) -> Dict:
        return self.analyze("Disable Encryption", [
            {"component": "pg-primary", "field": "encrypted", "value": False},
            {"component": "object-store", "field": "encrypted", "value": False},
        ])

    def what_if_region_failure(self) -> Dict:
        return self.analyze("US-East-1 Region Failure", [
            {"component": name, "field": "status", "value": ComponentStatus.DOWN}
            for name, comp in self._twin._components.items()
            if comp.region == "us-east-1"
        ])

    def what_if_unpatched(self) -> Dict:
        return self.analyze("Critical Patches Pending", [
            {"component": "api-gateway", "field": "patches_pending", "value": 3},
            {"component": "auth-service", "field": "patches_pending", "value": 2},
            {"component": "pg-primary", "field": "patches_pending", "value": 1},
        ])

    def get_stats(self) -> Dict:
        return {"analyses": len(self._analyses)}


# ============================================================================
#  ATTACK SIMULATION
# ============================================================================

class KillChainPhase(str, Enum):
    RECON = "reconnaissance"
    WEAPONIZE = "weaponization"
    DELIVER = "delivery"
    EXPLOIT = "exploitation"
    INSTALL = "installation"
    C2 = "command_and_control"
    ACTIONS = "actions_on_objectives"


class AttackStep:
    def __init__(self, phase, technique, target, success_prob):
        self.phase = phase
        self.technique = technique
        self.target = target
        self.success_prob = success_prob
        self.blocked = False
        self.detected = False

    def to_dict(self):
        return {"phase": self.phase.value, "technique": self.technique,
                "target": self.target,
                "blocked": self.blocked, "detected": self.detected}


class AttackSimulation:
    """Full kill-chain simulation against the digital twin."""

    KILL_CHAINS = {
        "apt_intrusion": [
            AttackStep(KillChainPhase.RECON, "OSINT + DNS enum", "dns", 0.9),
            AttackStep(KillChainPhase.WEAPONIZE, "Craft spearphish", "admin-users", 0.8),
            AttackStep(KillChainPhase.DELIVER, "Send phishing email", "admin-users", 0.7),
            AttackStep(KillChainPhase.EXPLOIT, "Credential harvest", "auth-service", 0.4),
            AttackStep(KillChainPhase.INSTALL, "Deploy backdoor", "api-gateway", 0.3),
            AttackStep(KillChainPhase.C2, "Establish C2 channel", "vpn-gateway", 0.2),
            AttackStep(KillChainPhase.ACTIONS, "Exfiltrate data", "pg-primary", 0.15),
        ],
        "ransomware": [
            AttackStep(KillChainPhase.RECON, "Scan for exposed RDP", "load-balancer", 0.8),
            AttackStep(KillChainPhase.DELIVER, "Exploit public service", "api-gateway", 0.5),
            AttackStep(KillChainPhase.EXPLOIT, "Privilege escalation", "auth-service", 0.3),
            AttackStep(KillChainPhase.INSTALL, "Deploy ransomware", "pg-primary", 0.2),
            AttackStep(KillChainPhase.ACTIONS, "Encrypt databases", "pg-primary", 0.1),
        ],
        "insider_threat": [
            AttackStep(KillChainPhase.RECON, "Map data stores", "object-store", 0.95),
            AttackStep(KillChainPhase.EXPLOIT, "Abuse valid credentials", "auth-service", 0.6),
            AttackStep(KillChainPhase.ACTIONS, "Bulk data download", "pg-primary", 0.4),
            AttackStep(KillChainPhase.ACTIONS, "Exfil via USB/cloud", "object-store", 0.3),
        ],
        "supply_chain": [
            AttackStep(KillChainPhase.RECON, "Identify dependencies", "verification-engine", 0.9),
            AttackStep(KillChainPhase.WEAPONIZE, "Inject malicious code", "verification-engine", 0.4),
            AttackStep(KillChainPhase.DELIVER, "Push via CI/CD", "api-gateway", 0.3),
            AttackStep(KillChainPhase.INSTALL, "Deploy in production", "security-hub", 0.2),
            AttackStep(KillChainPhase.C2, "Phone home callback", "vpn-gateway", 0.1),
        ],
    }

    def __init__(self, twin: DigitalTwin):
        self._twin = twin
        self._simulations: List[Dict] = []

    def simulate(self, kill_chain_name: str) -> Dict:
        chain = self.KILL_CHAINS.get(kill_chain_name)
        if not chain:
            return {"error": "Kill chain not found",
                    "available": list(self.KILL_CHAINS.keys())}

        steps_result = []
        chain_broken = False
        for step_template in chain:
            step = AttackStep(step_template.phase, step_template.technique,
                            step_template.target, step_template.success_prob)

            # Check twin's defenses
            comp = self._twin._components.get(step.target)
            defense_modifier = 1.0
            if comp:
                if comp.mfa_enabled:
                    defense_modifier *= 0.5
                if comp.encrypted:
                    defense_modifier *= 0.7
                if comp.config.get("waf"):
                    defense_modifier *= 0.4

            effective_prob = step.success_prob * defense_modifier
            succeeded = os.urandom(1)[0] / 255.0 < effective_prob

            if not succeeded:
                step.blocked = True
                step.detected = os.urandom(1)[0] > 50  # ~80% detection on block
                chain_broken = True

            step.detected = step.detected or (os.urandom(1)[0] > 100)  # ~60% general detection

            steps_result.append({
                **step.to_dict(),
                "success_prob": round(effective_prob, 3),
                "succeeded": not step.blocked,
            })

            if chain_broken:
                break

        breach_achieved = not chain_broken
        detection_rate = sum(1 for s in steps_result if s.get("detected", False)) / max(len(steps_result), 1) * 100
        furthest_phase = steps_result[-1]["phase"] if steps_result else "none"

        result = {
            "kill_chain": kill_chain_name,
            "steps": steps_result,
            "breach_achieved": breach_achieved,
            "furthest_phase": furthest_phase,
            "steps_completed": sum(1 for s in steps_result if s.get("succeeded", False)),
            "detection_rate": round(detection_rate, 1),
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._simulations.append(result)
        return result

    def run_all_simulations(self) -> Dict:
        results = []
        for name in self.KILL_CHAINS:
            results.append(self.simulate(name))
        breaches = sum(1 for r in results if r["breach_achieved"])
        return {
            "simulations": results,
            "total": len(results),
            "breaches": breaches,
            "resilience_score": round((1 - breaches / max(len(results), 1)) * 100),
        }

    def get_stats(self) -> Dict:
        return {"simulations": len(self._simulations)}


# Singletons
digital_twin = DigitalTwin()
what_if_engine = WhatIfEngine(digital_twin)
attack_simulation = AttackSimulation(digital_twin)
