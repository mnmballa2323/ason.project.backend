"""
Rate Limiter (Per-Tenant) — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Token-bucket rate limiting scoped by tenant + endpoint.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger("qwen.rate_limiter")


class TokenBucket:
    """
    Token bucket rate limiter.
    Tokens refill at a steady rate. Each request consumes one token.
    When empty, requests are rejected until tokens refill.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum tokens in the bucket
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens: float = capacity
        self._last_refill: float = time.time()

    def _refill(self):
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed, False if rate limited."""
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    @property
    def available_tokens(self) -> int:
        self._refill()
        return int(self._tokens)

    @property
    def time_until_available(self) -> float:
        """Seconds until at least 1 token is available."""
        if self._tokens >= 1:
            return 0.0
        deficit = 1 - self._tokens
        return deficit / self.refill_rate if self.refill_rate > 0 else float("inf")


# ============================================================================
#  RATE LIMIT TIERS
# ============================================================================

# Requests per minute by plan tier
TIER_LIMITS = {
    "starter": {
        "global": 100,           # 100 req/min total
        "verify_submit": 20,     # 20 verifications/min
        "verify_batch": 5,       # 5 batch jobs/min
        "audit_export": 10,      # 10 exports/min
        "websocket": 50,         # 50 WS messages/min
    },
    "professional": {
        "global": 500,
        "verify_submit": 100,
        "verify_batch": 20,
        "audit_export": 50,
        "websocket": 200,
    },
    "enterprise": {
        "global": 2000,
        "verify_submit": 500,
        "verify_batch": 100,
        "audit_export": 200,
        "websocket": 1000,
    },
    "government": {
        "global": 5000,
        "verify_submit": 1000,
        "verify_batch": 500,
        "audit_export": 500,
        "websocket": 2000,
    },
}


# ============================================================================
#  RATE LIMIT MANAGER
# ============================================================================

class RateLimitResult:
    """Result of a rate limit check."""

    def __init__(self, allowed: bool, limit: int, remaining: int, retry_after: float = 0.0):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.retry_after = retry_after

    def to_headers(self) -> Dict[str, str]:
        """Generate standard rate limit response headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
        }
        if not self.allowed:
            headers["Retry-After"] = str(int(self.retry_after) + 1)
            headers["X-RateLimit-Reset"] = str(int(time.time() + self.retry_after))
        return headers


class RateLimiter:
    """
    Per-tenant, per-endpoint rate limiter using token buckets.
    All in-memory — no Redis or external dependency.
    """

    def __init__(self):
        # Key: (tenant_id, endpoint) → TokenBucket
        self._buckets: Dict[Tuple[str, str], TokenBucket] = {}
        self._total_limited: int = 0
        self._total_allowed: int = 0

    def _get_bucket(self, tenant_id: str, endpoint: str, tier: str) -> TokenBucket:
        """Get or create a rate limit bucket for a tenant+endpoint."""
        key = (tenant_id, endpoint)
        if key not in self._buckets:
            limits = TIER_LIMITS.get(tier, TIER_LIMITS["starter"])
            capacity = limits.get(endpoint, limits.get("global", 100))
            # Convert per-minute to per-second refill rate
            refill_rate = capacity / 60.0
            self._buckets[key] = TokenBucket(capacity, refill_rate)
        return self._buckets[key]

    def check(self, tenant_id: str, endpoint: str = "global", tier: str = "enterprise") -> RateLimitResult:
        """
        Check and consume a rate limit token.
        Returns RateLimitResult with allowed status and headers.
        """
        bucket = self._get_bucket(tenant_id, endpoint, tier)
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["starter"])
        limit = limits.get(endpoint, limits.get("global", 100))

        if bucket.consume(1):
            self._total_allowed += 1
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=bucket.available_tokens,
            )
        else:
            self._total_limited += 1
            logger.warning(f"Rate limited: tenant={tenant_id} endpoint={endpoint}")
            return RateLimitResult(
                allowed=False,
                limit=limit,
                remaining=0,
                retry_after=bucket.time_until_available,
            )

    def get_tenant_status(self, tenant_id: str, tier: str = "enterprise") -> Dict:
        """Get rate limit status for all endpoints of a tenant."""
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["starter"])
        status = {}
        for endpoint, limit in limits.items():
            key = (tenant_id, endpoint)
            bucket = self._buckets.get(key)
            status[endpoint] = {
                "limit_per_min": limit,
                "remaining": bucket.available_tokens if bucket else limit,
                "utilization_pct": round(
                    ((limit - (bucket.available_tokens if bucket else limit)) / limit) * 100, 1
                ) if limit > 0 else 0,
            }
        return status

    def get_stats(self) -> Dict:
        return {
            "total_allowed": self._total_allowed,
            "total_limited": self._total_limited,
            "active_buckets": len(self._buckets),
            "rejection_rate_pct": round(
                (self._total_limited / max(1, self._total_allowed + self._total_limited)) * 100, 2
            ),
        }

    def cleanup_inactive(self, max_idle_seconds: int = 3600):
        """Remove buckets that haven't been used in `max_idle_seconds`."""
        cutoff = time.time() - max_idle_seconds
        expired = [key for key, bucket in self._buckets.items() if bucket._last_refill < cutoff]
        for key in expired:
            del self._buckets[key]
        if expired:
            logger.info(f"Cleaned up {len(expired)} idle rate limit buckets")


# Global singleton
rate_limiter = RateLimiter()
