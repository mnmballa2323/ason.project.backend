"""
API Abuse Detection — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Detects sophisticated API abuse patterns:
- Credential stuffing (distributed low-rate auth attacks)
- Account enumeration (timing and response analysis)
- Scraping & data harvesting (sequential access patterns)
- Token abuse (stolen/leaked token usage)
- Automated bot detection (request timing analysis)
"""

import collections
import logging
import math
import statistics
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("qwen.api_abuse")


class AbuseType(str, Enum):
    CREDENTIAL_STUFFING = "credential_stuffing"
    ACCOUNT_ENUMERATION = "account_enumeration"
    SCRAPING = "scraping"
    TOKEN_ABUSE = "token_abuse"
    BOT_ACTIVITY = "bot_activity"
    RATE_EVASION = "rate_evasion"


class AbuseAction(str, Enum):
    LOG = "log"
    WARN = "warn"
    THROTTLE = "throttle"
    CHALLENGE = "challenge"
    BLOCK = "block"


class AbuseIndicator:
    """A single detected abuse indicator."""
    def __init__(self, abuse_type, confidence, description,
                 action, actor_id="", source_ip="", evidence=None):
        self.abuse_type = abuse_type
        self.confidence = confidence  # 0.0-1.0
        self.description = description
        self.action = action
        self.actor_id = actor_id
        self.source_ip = source_ip
        self.evidence = evidence or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "type": self.abuse_type.value, "confidence": self.confidence,
            "description": self.description, "action": self.action.value,
            "actor_id": self.actor_id, "source_ip": self.source_ip,
            "evidence": self.evidence, "timestamp": self.timestamp,
        }


class SourceTracker:
    """Tracks request patterns from a single source (IP or actor)."""
    def __init__(self):
        self.request_times: collections.deque = collections.deque(maxlen=500)
        self.auth_attempts: collections.deque = collections.deque(maxlen=200)
        self.auth_failures: collections.deque = collections.deque(maxlen=200)
        self.endpoints: collections.Counter = collections.Counter()
        self.unique_usernames: set = set()
        self.tokens_seen: set = set()
        self.user_agents: set = set()
        self.response_sizes: collections.deque = collections.deque(maxlen=200)

    def record(self, endpoint, timestamp=None, user_agent="", token_hash=""):
        ts = timestamp or time.time()
        self.request_times.append(ts)
        self.endpoints[endpoint] += 1
        if user_agent:
            self.user_agents.add(user_agent)
        if token_hash:
            self.tokens_seen.add(token_hash)

    def record_auth(self, username, success, timestamp=None):
        ts = timestamp or time.time()
        self.auth_attempts.append((ts, username, success))
        if not success:
            self.auth_failures.append((ts, username))
        self.unique_usernames.add(username)

    def get_inter_arrival_times(self, window=300) -> List[float]:
        """Get time gaps between requests (bot detection)."""
        now = time.time()
        recent = sorted(t for t in self.request_times if t > now - window)
        if len(recent) < 3:
            return []
        return [recent[i+1] - recent[i] for i in range(len(recent)-1)]

    def get_auth_failure_rate(self, window=300) -> Tuple[int, int]:
        """(failures, total_attempts) in window."""
        now = time.time()
        cutoff = now - window
        total = sum(1 for t, _, _ in self.auth_attempts if t > cutoff)
        fails = sum(1 for t, _ in self.auth_failures if t > cutoff)
        return fails, total


class APIAbuseDetector:
    """Detects sophisticated API abuse patterns. All local."""

    def __init__(self):
        self._sources: Dict[str, SourceTracker] = {}
        self._indicators: List[AbuseIndicator] = []
        self._lock = threading.Lock()
        self._blocked: set = set()

    def _tracker(self, source_key: str) -> SourceTracker:
        if source_key not in self._sources:
            self._sources[source_key] = SourceTracker()
        return self._sources[source_key]

    def analyze_request(
        self, source_ip: str, endpoint: str, actor_id: str = "",
        user_agent: str = "", token_hash: str = "",
    ) -> List[AbuseIndicator]:
        """Analyze a request for abuse indicators."""
        key = source_ip
        tracker = self._tracker(key)
        tracker.record(endpoint, user_agent=user_agent, token_hash=token_hash)
        indicators = []

        # 1. Bot detection via request timing regularity
        iats = tracker.get_inter_arrival_times()
        if len(iats) >= 10:
            try:
                cv = statistics.stdev(iats) / max(statistics.mean(iats), 0.001)
                if cv < 0.1:  # Suspiciously regular timing
                    indicators.append(AbuseIndicator(
                        AbuseType.BOT_ACTIVITY, min(0.95, 1.0 - cv),
                        f"Robotic request timing (CV={cv:.3f})",
                        AbuseAction.CHALLENGE, actor_id, source_ip,
                        {"coefficient_of_variation": round(cv, 4),
                         "mean_interval": round(statistics.mean(iats), 3)},
                    ))
            except (statistics.StatisticsError, ZeroDivisionError):
                pass

        # 2. Scraping detection (sequential access to enumerable endpoints)
        if tracker.endpoints.most_common(1):
            top_endpoint, count = tracker.endpoints.most_common(1)[0]
            now = time.time()
            recent = sum(1 for t in tracker.request_times if t > now - 60)
            if count > 50 and recent > 20:
                indicators.append(AbuseIndicator(
                    AbuseType.SCRAPING, 0.8,
                    f"Scraping: {count} requests to {top_endpoint}",
                    AbuseAction.THROTTLE, actor_id, source_ip,
                    {"endpoint": top_endpoint, "count": count},
                ))

        # 3. Rate limit evasion (rotating user agents)
        if len(tracker.user_agents) > 10:
            indicators.append(AbuseIndicator(
                AbuseType.RATE_EVASION, 0.7,
                f"UA rotation: {len(tracker.user_agents)} unique agents",
                AbuseAction.WARN, actor_id, source_ip,
                {"unique_agents": len(tracker.user_agents)},
            ))

        # 4. Token abuse (many tokens from same IP)
        if len(tracker.tokens_seen) > 5:
            indicators.append(AbuseIndicator(
                AbuseType.TOKEN_ABUSE, 0.85,
                f"Multiple tokens from single IP: {len(tracker.tokens_seen)}",
                AbuseAction.BLOCK, actor_id, source_ip,
                {"tokens_count": len(tracker.tokens_seen)},
            ))

        with self._lock:
            self._indicators.extend(indicators)
        return indicators

    def analyze_auth(
        self, source_ip: str, username: str, success: bool,
    ) -> List[AbuseIndicator]:
        """Analyze authentication attempt for credential abuse."""
        tracker = self._tracker(source_ip)
        tracker.record_auth(username, success)
        indicators = []

        # 1. Credential stuffing (many usernames, mostly failures)
        if len(tracker.unique_usernames) > 5:
            fails, total = tracker.get_auth_failure_rate()
            if total > 0 and fails / total > 0.8:
                indicators.append(AbuseIndicator(
                    AbuseType.CREDENTIAL_STUFFING, 0.9,
                    f"Credential stuffing: {len(tracker.unique_usernames)} "
                    f"users, {fails}/{total} failures",
                    AbuseAction.BLOCK, "", source_ip,
                    {"unique_users": len(tracker.unique_usernames),
                     "failure_rate": round(fails/total, 2)},
                ))

        # 2. Account enumeration (testing many usernames)
        if len(tracker.unique_usernames) > 20:
            indicators.append(AbuseIndicator(
                AbuseType.ACCOUNT_ENUMERATION, 0.85,
                f"Account enumeration: {len(tracker.unique_usernames)} usernames tested",
                AbuseAction.BLOCK, "", source_ip,
                {"unique_users": len(tracker.unique_usernames)},
            ))

        with self._lock:
            self._indicators.extend(indicators)
        return indicators

    def is_blocked(self, source_ip: str) -> bool:
        return source_ip in self._blocked

    def block(self, source_ip: str, reason: str = ""):
        self._blocked.add(source_ip)
        logger.warning(f"API abuse: blocked {source_ip} — {reason}")

    def get_indicators(self, abuse_type: AbuseType = None, limit=100):
        results = self._indicators
        if abuse_type:
            results = [i for i in results if i.abuse_type == abuse_type]
        return [i.to_dict() for i in results[-limit:]]

    def get_stats(self) -> Dict:
        by_type = {}
        for i in self._indicators:
            by_type[i.abuse_type.value] = by_type.get(i.abuse_type.value, 0) + 1
        return {
            "total_indicators": len(self._indicators),
            "tracked_sources": len(self._sources),
            "blocked_sources": len(self._blocked),
            "by_type": by_type,
        }

api_abuse_detector = APIAbuseDetector()
