"""
Threat Emulation Framework — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

MITRE ATT&CK adversary emulation, purple team, tabletop exercises.
"""

import hashlib, logging, os, threading, time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.threat_emulation")


# ============================================================================
#  ADVERSARY EMULATION
# ============================================================================

class TacticPhase(str, Enum):
    RECON = "reconnaissance"
    RESOURCE_DEV = "resource_development"
    INITIAL_ACCESS = "initial_access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    PRIV_ESC = "privilege_escalation"
    DEFENSE_EVASION = "defense_evasion"
    CRED_ACCESS = "credential_access"
    DISCOVERY = "discovery"
    LATERAL = "lateral_movement"
    COLLECTION = "collection"
    C2 = "command_and_control"
    EXFIL = "exfiltration"
    IMPACT = "impact"


class ATTCKTechnique:
    def __init__(self, technique_id, name, tactic, description):
        self.technique_id = technique_id
        self.name = name
        self.tactic = tactic
        self.description = description

    def to_dict(self):
        return {"id": self.technique_id, "name": self.name,
                "tactic": self.tactic.value}


class AdversaryProfile:
    def __init__(self, name, aliases, origin, sophistication, techniques):
        self.name = name
        self.aliases = aliases
        self.origin = origin
        self.sophistication = sophistication  # 1-10
        self.techniques: List[ATTCKTechnique] = techniques
        self.emulations_run = 0

    def to_dict(self):
        return {"name": self.name, "aliases": self.aliases,
                "origin": self.origin, "sophistication": self.sophistication,
                "techniques": len(self.techniques)}


class AdversaryEmulation:
    """MITRE ATT&CK-based adversary emulation engine."""

    def __init__(self):
        self._adversaries: Dict[str, AdversaryProfile] = {}
        self._results: List[Dict] = []
        self._seed()

    def _seed(self):
        # APT29 (Cozy Bear) — Russia/SVR
        apt29 = AdversaryProfile("APT29", ["Cozy Bear", "Nobelium", "Midnight Blizzard"],
                                "Russia/SVR", 9, [
            ATTCKTechnique("T1566.001", "Spearphishing Attachment", TacticPhase.INITIAL_ACCESS,
                          "Sends targeted phishing with malicious attachments"),
            ATTCKTechnique("T1059.001", "PowerShell Execution", TacticPhase.EXECUTION,
                          "Uses PowerShell for command execution"),
            ATTCKTechnique("T1053.005", "Scheduled Task", TacticPhase.PERSISTENCE,
                          "Creates scheduled tasks for persistence"),
            ATTCKTechnique("T1078", "Valid Accounts", TacticPhase.PRIV_ESC,
                          "Compromises legitimate credentials"),
            ATTCKTechnique("T1027", "Obfuscated Files", TacticPhase.DEFENSE_EVASION,
                          "Uses code obfuscation to evade detection"),
            ATTCKTechnique("T1003.001", "LSASS Memory Dump", TacticPhase.CRED_ACCESS,
                          "Dumps LSASS process memory for credentials"),
            ATTCKTechnique("T1021.002", "SMB/Windows Admin Shares", TacticPhase.LATERAL,
                          "Uses SMB for lateral movement"),
            ATTCKTechnique("T1071.001", "Web Protocols C2", TacticPhase.C2,
                          "Uses HTTPS for C2 communication"),
        ])
        self._adversaries["APT29"] = apt29

        # APT41 (Double Dragon) — China/MSS
        apt41 = AdversaryProfile("APT41", ["Double Dragon", "Wicked Panda", "Barium"],
                                "China/MSS", 9, [
            ATTCKTechnique("T1190", "Exploit Public-Facing App", TacticPhase.INITIAL_ACCESS,
                          "Exploits web application vulnerabilities"),
            ATTCKTechnique("T1059.003", "Windows Command Shell", TacticPhase.EXECUTION,
                          "Uses cmd.exe for execution"),
            ATTCKTechnique("T1547.001", "Registry Run Keys", TacticPhase.PERSISTENCE,
                          "Modifies registry for persistence"),
            ATTCKTechnique("T1055", "Process Injection", TacticPhase.DEFENSE_EVASION,
                          "Injects code into legitimate processes"),
            ATTCKTechnique("T1560.001", "Archive via Utility", TacticPhase.COLLECTION,
                          "Uses compression tools to stage data"),
            ATTCKTechnique("T1048.002", "Exfil Over Asymmetric Encrypted", TacticPhase.EXFIL,
                          "Exfiltrates data over encrypted channels"),
        ])
        self._adversaries["APT41"] = apt41

        # FIN7 — Financial Crime
        fin7 = AdversaryProfile("FIN7", ["Carbanak", "Carbon Spider"],
                               "Eastern Europe", 8, [
            ATTCKTechnique("T1566.002", "Spearphishing Link", TacticPhase.INITIAL_ACCESS,
                          "Phishing with malicious links"),
            ATTCKTechnique("T1059.005", "Visual Basic Execution", TacticPhase.EXECUTION,
                          "Uses VBA macros"),
            ATTCKTechnique("T1543.003", "Windows Service", TacticPhase.PERSISTENCE,
                          "Creates malicious Windows services"),
            ATTCKTechnique("T1005", "Data from Local System", TacticPhase.COLLECTION,
                          "Collects data from local file system"),
        ])
        self._adversaries["FIN7"] = fin7

        # Lazarus Group — North Korea
        lazarus = AdversaryProfile("Lazarus", ["Hidden Cobra", "Zinc", "Diamond Sleet"],
                                  "North Korea/RGB", 8, [
            ATTCKTechnique("T1195.002", "Supply Chain Compromise", TacticPhase.INITIAL_ACCESS,
                          "Compromises software supply chain"),
            ATTCKTechnique("T1059.006", "Python Execution", TacticPhase.EXECUTION,
                          "Uses Python for execution"),
            ATTCKTechnique("T1112", "Modify Registry", TacticPhase.DEFENSE_EVASION,
                          "Modifies registry to hide artifacts"),
            ATTCKTechnique("T1486", "Data Encrypted for Impact", TacticPhase.IMPACT,
                          "Deploys ransomware"),
            ATTCKTechnique("T1071.004", "DNS C2", TacticPhase.C2,
                          "Uses DNS for C2 communication"),
        ])
        self._adversaries["Lazarus"] = lazarus

    def emulate(self, adversary_name: str) -> Dict:
        adv = self._adversaries.get(adversary_name)
        if not adv:
            return {"error": "Adversary not found"}
        adv.emulations_run += 1
        step_results = []
        for tech in adv.techniques:
            detected = os.urandom(1)[0] > 64  # ~75% detection rate
            step_results.append({
                "technique": tech.to_dict(),
                "detected": detected,
                "blocked": detected and os.urandom(1)[0] > 128,
            })
        detected_pct = sum(1 for s in step_results if s["detected"]) / max(len(step_results), 1) * 100
        blocked_pct = sum(1 for s in step_results if s["blocked"]) / max(len(step_results), 1) * 100
        result = {
            "adversary": adv.to_dict(),
            "techniques_tested": len(step_results),
            "detection_rate": round(detected_pct, 1),
            "block_rate": round(blocked_pct, 1),
            "steps": step_results,
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._results.append(result)
        return result

    def get_stats(self) -> Dict:
        return {"adversaries": len(self._adversaries),
                "emulations": len(self._results)}


# ============================================================================
#  PURPLE TEAM ENGINE
# ============================================================================

class PurpleTeamExercise:
    def __init__(self, exercise_id, name, attack_steps, defense_checks):
        self.exercise_id = exercise_id
        self.name = name
        self.attack_steps = attack_steps
        self.defense_checks = defense_checks
        self.runs = 0

    def to_dict(self):
        return {"id": self.exercise_id, "name": self.name,
                "attacks": len(self.attack_steps),
                "defenses": len(self.defense_checks)}


class PurpleTeamEngine:
    """Automated purple team — attack + defend + measure simultaneously."""

    def __init__(self):
        self._exercises: Dict[str, PurpleTeamExercise] = {}
        self._results: List[Dict] = []
        self._seed()

    def _seed(self):
        exercises = [
            ("PT-001", "Credential Theft & Response",
             ["phish_employee", "harvest_creds", "lateral_move", "access_crown_jewel"],
             ["detect_phishing", "mfa_challenge", "anomaly_detect", "auto_contain"]),
            ("PT-002", "Ransomware Simulation",
             ["initial_access", "disable_av", "encrypt_files", "drop_ransom_note"],
             ["detect_av_tamper", "fim_alert", "isolate_host", "restore_from_backup"]),
            ("PT-003", "Data Exfiltration",
             ["recon_data_stores", "stage_data", "compress_encrypt", "exfil_dns"],
             ["dlp_detect", "anomaly_volume", "dns_monitoring", "block_exfil"]),
            ("PT-004", "Supply Chain Attack",
             ["compromise_dep", "inject_backdoor", "trigger_build", "deploy_malicious"],
             ["sbom_verify", "code_signing_check", "runtime_integrity", "rollback"]),
            ("PT-005", "Insider Threat",
             ["abuse_access", "hoard_data", "install_tool", "exfil_usb"],
             ["ueba_detect", "dlp_alert", "tool_whitelist", "endpoint_block"]),
        ]
        for eid, name, attacks, defenses in exercises:
            self._exercises[eid] = PurpleTeamExercise(eid, name, attacks, defenses)

    def run_exercise(self, exercise_id: str) -> Dict:
        ex = self._exercises.get(exercise_id)
        if not ex:
            return {"error": "Exercise not found"}
        ex.runs += 1
        attack_results = []
        defense_results = []
        for i, (attack, defense) in enumerate(zip(ex.attack_steps, ex.defense_checks)):
            attack_success = os.urandom(1)[0] > 100  # ~60% attack success
            defense_success = os.urandom(1)[0] > 80  # ~68% defense success
            attack_results.append({"step": attack, "success": attack_success})
            defense_results.append({"check": defense, "detected": defense_success,
                                   "responded": defense_success and os.urandom(1)[0] > 64})
        detection_rate = sum(1 for d in defense_results if d["detected"]) / max(len(defense_results), 1) * 100
        response_rate = sum(1 for d in defense_results if d.get("responded")) / max(len(defense_results), 1) * 100
        result = {
            "exercise": ex.to_dict(), "attacks": attack_results,
            "defenses": defense_results,
            "detection_rate": round(detection_rate, 1),
            "response_rate": round(response_rate, 1),
            "score": round((detection_rate + response_rate) / 2, 1),
            "ts": datetime.now(timezone.utc).isoformat()}
        self._results.append(result)
        return result

    def get_stats(self) -> Dict:
        return {"exercises": len(self._exercises),
                "runs": sum(e.runs for e in self._exercises.values())}


# ============================================================================
#  TABLETOP EXERCISE ENGINE
# ============================================================================

class TTXScenario:
    def __init__(self, name, description, injects, decision_points, duration_min):
        self.name = name
        self.description = description
        self.injects = injects  # Timeline events
        self.decision_points = decision_points
        self.duration_min = duration_min
        self.runs = 0

    def to_dict(self):
        return {"name": self.name, "injects": len(self.injects),
                "decisions": len(self.decision_points),
                "duration_min": self.duration_min}


class TabletopExerciseEngine:
    """Scenario-driven war games for IR teams."""

    def __init__(self):
        self._scenarios: Dict[str, TTXScenario] = {}
        self._results: List[Dict] = []
        self._seed()

    def _seed(self):
        scenarios = [
            ("ransomware_attack", "Ransomware hits production at 2 AM", [
                {"t+0min": "SOC receives alert: unusual file encryption activity on prod-web-01"},
                {"t+5min": "Additional hosts reporting encryption: prod-web-02, prod-db-01"},
                {"t+10min": "Ransom note discovered on encrypted systems"},
                {"t+15min": "Attacker sends ransom demand: 50 BTC within 72 hours"},
                {"t+30min": "Media outlet contacts PR about potential breach"},
                {"t+60min": "Customers report service outage on social media"},
            ], [
                "Do you pay the ransom?",
                "When do you notify law enforcement?",
                "Do you disclose to customers before investigation is complete?",
                "How do you communicate with the board?",
                "When do you engage external IR firm?",
            ], 120),
            ("supply_chain_compromise", "Compromised dependency in CI/CD", [
                {"t+0min": "Automated SBOM scan flags new dependency with unusual behavior"},
                {"t+5min": "Dependency makes outbound connection to unknown C2 server"},
                {"t+15min": "Analysis reveals backdoor in popular open-source package"},
                {"t+30min": "Same package used by 3 other production services"},
                {"t+45min": "CISA issues emergency directive about the package"},
            ], [
                "Do you halt all deployments immediately?",
                "How do you assess blast radius across services?",
                "When do you notify affected customers?",
                "How do you validate existing production builds?",
            ], 90),
            ("insider_data_theft", "Senior engineer stealing IP before resignation", [
                {"t+0min": "UEBA flags unusual data access pattern for senior engineer"},
                {"t+5min": "DLP detects bulk download of proprietary source code"},
                {"t+15min": "HR confirms engineer submitted resignation yesterday"},
                {"t+30min": "Engineer's access badge used at unusual hours"},
                {"t+45min": "External USB device detected on engineer's workstation"},
            ], [
                "Do you immediately revoke access or monitor covertly?",
                "When do you involve legal and HR?",
                "Do you forensically image the workstation while employee is present?",
                "How do you handle if stolen data appears at a competitor?",
            ], 60),
            ("zero_day_exploit", "Zero-day in authentication service", [
                {"t+0min": "Anomalous auth bypass detected by UEBA — no credential used"},
                {"t+10min": "Exploit code found circulating on underground forum"},
                {"t+20min": "Vendor confirms zero-day, no patch available"},
                {"t+30min": "Active exploitation detected in the wild"},
                {"t+60min": "Vendor releases emergency patch"},
            ], [
                "Do you take auth service offline pending patch?",
                "How do you implement compensating controls?",
                "When do you conduct threat hunt for prior exploitation?",
            ], 90),
        ]
        for name, desc, injects, decisions, dur in scenarios:
            self._scenarios[name] = TTXScenario(name, desc, injects, decisions, dur)

    def run_exercise(self, scenario_name: str, decisions: Dict[str, str] = None) -> Dict:
        scenario = self._scenarios.get(scenario_name)
        if not scenario:
            return {"error": "Scenario not found"}
        scenario.runs += 1
        result = {
            "scenario": scenario.to_dict(),
            "injects": scenario.injects,
            "decision_points": scenario.decision_points,
            "decisions_made": decisions or {},
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        self._results.append(result)
        return result

    def list_scenarios(self) -> List[Dict]:
        return [s.to_dict() for s in self._scenarios.values()]

    def get_stats(self) -> Dict:
        return {"scenarios": len(self._scenarios),
                "runs": sum(s.runs for s in self._scenarios.values())}


# Singletons
adversary_emulation = AdversaryEmulation()
purple_team = PurpleTeamEngine()
ttx_engine = TabletopExerciseEngine()
