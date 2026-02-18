"""
Threat Intelligence Fusion — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Multi-source correlation engine that fuses intelligence from:
- IDS findings
- APT detector kill chain
- Deception tripwires
- API abuse indicators
- Threat hunting IOC sweeps
- SIEM event correlations

Produces unified Threat Intelligence Products (TIPs).
NASDAQ 100 Requirement: single pane of glass for threat intelligence.
"""

import hashlib
import logging
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.threat_fusion")


class IntelSource(str, Enum):
    IDS = "intrusion_detection"
    APT = "apt_detector"
    DECEPTION = "deception"
    API_ABUSE = "api_abuse"
    THREAT_HUNT = "threat_hunting"
    SIEM = "security_events"
    VULN_SCAN = "vulnerability_scanner"
    SERVICE_MESH = "service_mesh"
    PENTEST = "pentest_framework"
    EXTERNAL = "external_feed"


class ThreatLevel(str, Enum):
    CRITICAL = "critical"   # Active breach, immediate response
    HIGH = "high"           # Active attack, rapid response
    ELEVATED = "elevated"   # Increased risk, enhanced monitoring
    GUARDED = "guarded"     # General awareness
    LOW = "low"             # Normal operations


class ThreatIndicator:
    """A fused threat intelligence indicator."""
    def __init__(self, indicator_id, indicator_type, value,
                 confidence, sources):
        self.indicator_id = indicator_id
        self.indicator_type = indicator_type  # ip, domain, hash, behavior, etc.
        self.value = value
        self.confidence = confidence  # 0.0-1.0
        self.sources = sources        # List of IntelSource that reported this
        self.first_seen = datetime.now(timezone.utc)
        self.last_seen = self.first_seen
        self.sightings = 1
        self.tags: List[str] = []
        self.related: List[str] = []  # Related indicator IDs

    def update(self, source: IntelSource, confidence: float):
        self.sightings += 1
        self.last_seen = datetime.now(timezone.utc)
        if source.value not in self.sources:
            self.sources.append(source.value)
        # Multi-source confidence boost
        self.confidence = min(1.0, self.confidence + confidence * 0.1)

    def to_dict(self):
        return {
            "id": self.indicator_id,
            "type": self.indicator_type,
            "value": self.value[:50],
            "confidence": round(self.confidence, 3),
            "sources": self.sources,
            "source_count": len(self.sources),
            "sightings": self.sightings,
            "tags": self.tags,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
        }


class ThreatIntelProduct:
    """A Threat Intelligence Product — actionable summary."""
    def __init__(self, tip_id, title, threat_level, summary,
                 indicators, recommended_actions):
        self.tip_id = tip_id
        self.title = title
        self.threat_level = threat_level
        self.summary = summary
        self.indicators = indicators
        self.recommended_actions = recommended_actions
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.acknowledged = False

    def to_dict(self):
        return {
            "tip_id": self.tip_id, "title": self.title,
            "threat_level": self.threat_level.value,
            "summary": self.summary,
            "indicators": len(self.indicators),
            "actions": self.recommended_actions,
            "created_at": self.created_at,
            "acknowledged": self.acknowledged,
        }


class ThreatFusionEngine:
    """Fuses intelligence from all security subsystems."""

    def __init__(self):
        self._indicators: Dict[str, ThreatIndicator] = {}
        self._products: List[ThreatIntelProduct] = []
        self._lock = threading.Lock()
        self._counter = 0
        self._tip_counter = 0
        self._current_threat_level = ThreatLevel.LOW
        self._source_health: Dict[str, Dict] = {
            s.value: {"last_seen": None, "events": 0}
            for s in IntelSource
        }

    def ingest(self, source: IntelSource, indicator_type: str,
               value: str, confidence: float = 0.5,
               tags: List[str] = None) -> ThreatIndicator:
        """Ingest an intelligence indicator from any source."""
        # Deduplicate by value
        key = hashlib.sha256(f"{indicator_type}:{value}".encode()).hexdigest()[:16]
        with self._lock:
            if key in self._indicators:
                indicator = self._indicators[key]
                indicator.update(source, confidence)
            else:
                self._counter += 1
                indicator = ThreatIndicator(
                    f"TI-{self._counter:08d}", indicator_type,
                    value, confidence, [source.value],
                )
                if tags:
                    indicator.tags = tags
                self._indicators[key] = indicator

            # Update source health
            self._source_health[source.value]["last_seen"] = (
                datetime.now(timezone.utc).isoformat())
            self._source_health[source.value]["events"] += 1

        # Auto-elevate threat level based on indicator density
        self._recalculate_threat_level()

        return indicator

    def correlate(self, time_window_minutes: int = 60) -> List[Dict]:
        """Find correlated indicators across sources."""
        correlations = []
        indicators = list(self._indicators.values())

        for i, ind_a in enumerate(indicators):
            for ind_b in indicators[i+1:]:
                # Same value from different sources = high correlation
                if (ind_a.value == ind_b.value and
                        set(ind_a.sources) != set(ind_b.sources)):
                    correlations.append({
                        "type": "same_value_multi_source",
                        "indicator_a": ind_a.indicator_id,
                        "indicator_b": ind_b.indicator_id,
                        "value": ind_a.value[:30],
                        "combined_sources": list(set(ind_a.sources + ind_b.sources)),
                        "confidence": min(1.0, ind_a.confidence + ind_b.confidence),
                    })

        return correlations

    def generate_tip(self, title: str, threat_level: ThreatLevel,
                     summary: str, indicator_ids: List[str],
                     actions: List[str]) -> ThreatIntelProduct:
        """Generate a Threat Intelligence Product."""
        with self._lock:
            self._tip_counter += 1
            tip_id = f"TIP-{self._tip_counter:06d}"
        tip = ThreatIntelProduct(tip_id, title, threat_level,
                                 summary, indicator_ids, actions)
        self._products.append(tip)
        logger.warning(f"TIP generated: {title} [{threat_level.value}]")
        return tip

    def _recalculate_threat_level(self):
        high_conf = sum(1 for i in self._indicators.values()
                        if i.confidence >= 0.8)
        multi_source = sum(1 for i in self._indicators.values()
                           if len(i.sources) >= 3)
        if high_conf >= 10 or multi_source >= 5:
            self._current_threat_level = ThreatLevel.CRITICAL
        elif high_conf >= 5 or multi_source >= 3:
            self._current_threat_level = ThreatLevel.HIGH
        elif high_conf >= 2:
            self._current_threat_level = ThreatLevel.ELEVATED
        elif high_conf >= 1:
            self._current_threat_level = ThreatLevel.GUARDED
        else:
            self._current_threat_level = ThreatLevel.LOW

    def get_threat_level(self) -> Dict:
        return {
            "current_level": self._current_threat_level.value,
            "total_indicators": len(self._indicators),
            "high_confidence_indicators": sum(
                1 for i in self._indicators.values() if i.confidence >= 0.8),
            "multi_source_indicators": sum(
                1 for i in self._indicators.values() if len(i.sources) >= 2),
            "active_sources": sum(
                1 for s in self._source_health.values() if s["events"] > 0),
            "total_sources": len(IntelSource),
        }

    def get_source_health(self) -> Dict:
        return self._source_health

    def get_stats(self) -> Dict:
        return {
            "threat_level": self._current_threat_level.value,
            "indicators": len(self._indicators),
            "tips_generated": len(self._products),
            "source_coverage": sum(
                1 for s in self._source_health.values() if s["events"] > 0
            ) / len(IntelSource) * 100,
        }

threat_fusion = ThreatFusionEngine()
