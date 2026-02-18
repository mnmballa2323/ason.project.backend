"""
SLA Dashboard & SLO Engine — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Tracks uptime, latency percentiles, error budgets, and SLO compliance.
"""

import math
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Dict, List, Optional


# ============================================================================
#  SLO DEFINITIONS
# ============================================================================

class SLOTarget:
    """Service Level Objective definition."""

    def __init__(
        self, name: str, metric: str, target: float,
        window_hours: int = 720, tier: str = "enterprise",
    ):
        self.name = name
        self.metric = metric        # "availability" | "latency_p95" | "error_rate"
        self.target = target         # e.g., 99.99 (percent) or 200 (ms)
        self.window_hours = window_hours  # Rolling window (default 30 days)
        self.tier = tier

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "metric": self.metric,
            "target": self.target,
            "window_hours": self.window_hours,
            "tier": self.tier,
        }


# Default SLO targets by tier
SLO_TARGETS = {
    "starter": [
        SLOTarget("API Availability", "availability", 99.0, tier="starter"),
        SLOTarget("P95 Latency", "latency_p95", 2000, tier="starter"),   # 2s
        SLOTarget("Error Rate", "error_rate", 5.0, tier="starter"),       # 5%
    ],
    "professional": [
        SLOTarget("API Availability", "availability", 99.9, tier="professional"),
        SLOTarget("P95 Latency", "latency_p95", 1000, tier="professional"),
        SLOTarget("Error Rate", "error_rate", 1.0, tier="professional"),
    ],
    "enterprise": [
        SLOTarget("API Availability", "availability", 99.99, tier="enterprise"),
        SLOTarget("P95 Latency", "latency_p95", 500, tier="enterprise"),  # 500ms
        SLOTarget("Error Rate", "error_rate", 0.1, tier="enterprise"),
        SLOTarget("Verification Accuracy", "accuracy", 95.0, tier="enterprise"),
    ],
    "government": [
        SLOTarget("API Availability", "availability", 99.999, tier="government"),
        SLOTarget("P95 Latency", "latency_p95", 300, tier="government"),
        SLOTarget("Error Rate", "error_rate", 0.01, tier="government"),
        SLOTarget("Verification Accuracy", "accuracy", 99.0, tier="government"),
        SLOTarget("Audit Chain Integrity", "audit_integrity", 100.0, tier="government"),
    ],
}


# ============================================================================
#  METRICS COLLECTOR
# ============================================================================

class MetricsCollector:
    """Collects and computes SLA metrics in-memory."""

    def __init__(self, max_data_points: int = 100000):
        self._latencies: deque = deque(maxlen=max_data_points)
        self._requests: deque = deque(maxlen=max_data_points)    # (timestamp, success)
        self._errors: deque = deque(maxlen=max_data_points)
        self._start_time: float = time.time()
        self._total_requests: int = 0
        self._total_errors: int = 0
        self._downtime_seconds: float = 0
        self._last_health_check: float = time.time()
        self._is_healthy: bool = True

    def record_request(self, latency_ms: float, success: bool, endpoint: str = ""):
        """Record a request with its latency and outcome."""
        now = time.time()
        self._latencies.append((now, latency_ms))
        self._requests.append((now, success))
        self._total_requests += 1
        if not success:
            self._errors.append((now, endpoint))
            self._total_errors += 1

    def record_health_check(self, is_healthy: bool):
        """Record a health check result to track uptime."""
        now = time.time()
        if not is_healthy and self._is_healthy:
            # Transition to unhealthy
            self._last_health_check = now
        elif is_healthy and not self._is_healthy:
            # Recovered — add downtime
            self._downtime_seconds += now - self._last_health_check
        self._is_healthy = is_healthy
        self._last_health_check = now

    def get_availability(self, window_hours: int = 720) -> float:
        """Calculate availability percentage over the rolling window."""
        total_seconds = min(time.time() - self._start_time, window_hours * 3600)
        if total_seconds <= 0:
            return 100.0
        uptime = total_seconds - self._downtime_seconds
        return round((uptime / total_seconds) * 100, 4)

    def get_latency_percentile(self, percentile: float, window_hours: int = 1) -> float:
        """Calculate latency at a given percentile (e.g., 95th)."""
        cutoff = time.time() - (window_hours * 3600)
        latencies = sorted(
            [lat for ts, lat in self._latencies if ts >= cutoff]
        )
        if not latencies:
            return 0.0

        idx = int(math.ceil(percentile / 100 * len(latencies))) - 1
        return round(latencies[max(0, idx)], 2)

    def get_error_rate(self, window_hours: int = 1) -> float:
        """Calculate error rate percentage over the window."""
        cutoff = time.time() - (window_hours * 3600)
        total = sum(1 for ts, _ in self._requests if ts >= cutoff)
        errors = sum(1 for ts, success in self._requests if ts >= cutoff and not success)
        if total == 0:
            return 0.0
        return round((errors / total) * 100, 4)

    def get_throughput(self, window_hours: int = 1) -> float:
        """Requests per second over the window."""
        cutoff = time.time() - (window_hours * 3600)
        count = sum(1 for ts, _ in self._requests if ts >= cutoff)
        window_seconds = min(time.time() - self._start_time, window_hours * 3600)
        if window_seconds <= 0:
            return 0.0
        return round(count / window_seconds, 2)


# ============================================================================
#  SLA DASHBOARD
# ============================================================================

class SLADashboard:
    """Generates SLA dashboard data for the admin portal."""

    def __init__(self):
        self._collectors: Dict[str, MetricsCollector] = {}  # tenant_id -> collector
        self._global_collector = MetricsCollector()

    def get_collector(self, tenant_id: str = "global") -> MetricsCollector:
        if tenant_id == "global":
            return self._global_collector
        if tenant_id not in self._collectors:
            self._collectors[tenant_id] = MetricsCollector()
        return self._collectors[tenant_id]

    def record(self, tenant_id: str, latency_ms: float, success: bool, endpoint: str = ""):
        """Record a request for both tenant and global metrics."""
        self._global_collector.record_request(latency_ms, success, endpoint)
        self.get_collector(tenant_id).record_request(latency_ms, success, endpoint)

    def get_slo_status(self, tenant_id: str, tier: str = "enterprise") -> Dict:
        """Get current SLO compliance status for a tenant."""
        collector = self.get_collector(tenant_id)
        targets = SLO_TARGETS.get(tier, SLO_TARGETS["enterprise"])
        results = []

        for slo in targets:
            if slo.metric == "availability":
                actual = collector.get_availability(slo.window_hours)
                compliant = actual >= slo.target
                error_budget_pct = max(0, actual - slo.target) / (100 - slo.target) * 100 if slo.target < 100 else 100
            elif slo.metric == "latency_p95":
                actual = collector.get_latency_percentile(95, window_hours=1)
                compliant = actual <= slo.target
                error_budget_pct = max(0, (slo.target - actual) / slo.target * 100) if actual > 0 else 100
            elif slo.metric == "error_rate":
                actual = collector.get_error_rate(window_hours=1)
                compliant = actual <= slo.target
                error_budget_pct = max(0, (slo.target - actual) / slo.target * 100) if slo.target > 0 else 100
            else:
                actual = 100.0
                compliant = True
                error_budget_pct = 100

            results.append({
                "slo": slo.to_dict(),
                "actual": actual,
                "compliant": compliant,
                "error_budget_remaining_pct": round(min(100, error_budget_pct), 2),
                "status": "✅ OK" if compliant else "🔴 BREACH",
            })

        all_compliant = all(r["compliant"] for r in results)
        return {
            "tenant_id": tenant_id,
            "tier": tier,
            "overall_status": "healthy" if all_compliant else "degraded",
            "slos": results,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_dashboard_summary(self) -> Dict:
        """Global platform SLA summary for super admins."""
        gc = self._global_collector
        return {
            "platform": {
                "availability": gc.get_availability(),
                "p50_latency_ms": gc.get_latency_percentile(50),
                "p95_latency_ms": gc.get_latency_percentile(95),
                "p99_latency_ms": gc.get_latency_percentile(99),
                "error_rate_pct": gc.get_error_rate(),
                "throughput_rps": gc.get_throughput(),
                "total_requests": gc._total_requests,
                "total_errors": gc._total_errors,
                "uptime_hours": round((time.time() - gc._start_time) / 3600, 2),
            },
            "tenants_tracked": len(self._collectors),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


# Global singleton
sla_dashboard = SLADashboard()
