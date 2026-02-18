"""
Circuit Breaker — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Prevents cascade failures when downstream services fail.
Implements the three-state circuit breaker pattern:
  CLOSED → OPEN → HALF_OPEN → CLOSED
"""

import asyncio
import logging
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("qwen.circuit_breaker")


class CircuitState(str, Enum):
    CLOSED = "closed"        # Normal operation — requests pass through
    OPEN = "open"            # Failures exceeded threshold — requests rejected
    HALF_OPEN = "half_open"  # Trial period — single request allowed to test recovery


class CircuitBreakerError(Exception):
    """Raised when circuit is OPEN and calls are rejected."""
    def __init__(self, name: str, state: CircuitState, recovery_in: float):
        self.name = name
        self.state = state
        self.recovery_in = recovery_in
        super().__init__(
            f"Circuit '{name}' is {state.value}. "
            f"Recovery attempt in {recovery_in:.1f}s"
        )


class CircuitBreaker:
    """
    Thread-safe circuit breaker for protecting downstream service calls.

    Usage:
        inference_breaker = CircuitBreaker("inference", failure_threshold=5)

        @inference_breaker
        async def call_inference(prompt):
            return await http_client.post(INFERENCE_URL, ...)

    Or manual:
        async with inference_breaker:
            result = await call_inference(prompt)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
        success_threshold: int = 3,
        excluded_exceptions: tuple = (),
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.success_threshold = success_threshold
        self.excluded_exceptions = excluded_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_failure_time: float = 0
        self._half_open_calls: int = 0
        self._total_calls: int = 0
        self._total_failures: int = 0
        self._total_rejections: int = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                self._success_count = 0
                logger.info(f"Circuit '{self.name}' → HALF_OPEN (recovery window)")
        return self._state

    @property
    def recovery_in(self) -> float:
        if self._state != CircuitState.OPEN:
            return 0.0
        elapsed = time.time() - self._last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    def _record_success(self):
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"Circuit '{self.name}' → CLOSED (recovered)")
        else:
            self._failure_count = max(0, self._failure_count - 1)

    def _record_failure(self):
        """Record a failed call."""
        self._failure_count += 1
        self._total_failures += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit '{self.name}' → OPEN (half-open test failed)")
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                f"Circuit '{self.name}' → OPEN "
                f"({self._failure_count}/{self.failure_threshold} failures)"
            )

    async def _check_state(self):
        """Check if the call is allowed through the circuit."""
        current = self.state  # Property triggers OPEN → HALF_OPEN transition

        if current == CircuitState.CLOSED:
            return  # Allow

        if current == CircuitState.OPEN:
            self._total_rejections += 1
            raise CircuitBreakerError(self.name, current, self.recovery_in)

        if current == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerError(self.name, current, 0)
            self._half_open_calls += 1

    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker."""
        async with self._lock:
            await self._check_state()

        self._total_calls += 1
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.excluded_exceptions:
            self._record_success()
            raise
        except Exception:
            self._record_failure()
            raise

    def __call__(self, func):
        """Decorator to wrap an async function with circuit breaker."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.execute(func, *args, **kwargs)
        wrapper.circuit_breaker = self
        return wrapper

    async def __aenter__(self):
        async with self._lock:
            await self._check_state()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._record_success()
        elif not issubclass(exc_type, self.excluded_exceptions):
            self._record_failure()
        return False

    def reset(self):
        """Manually reset the circuit to CLOSED."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._half_open_calls = 0
        logger.info(f"Circuit '{self.name}' manually reset → CLOSED")

    def get_status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_in_seconds": round(self.recovery_in, 1),
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "total_rejections": self._total_rejections,
        }


# ============================================================================
#  PRE-CONFIGURED CIRCUIT BREAKERS
# ============================================================================

# Inference engine — fails fast if model server is down
inference_breaker = CircuitBreaker(
    "inference",
    failure_threshold=3,
    recovery_timeout=15.0,
    success_threshold=2,
)

# PostgreSQL — more tolerant, longer recovery
database_breaker = CircuitBreaker(
    "database",
    failure_threshold=5,
    recovery_timeout=30.0,
    success_threshold=3,
)

# Milvus vector store
vector_breaker = CircuitBreaker(
    "milvus",
    failure_threshold=5,
    recovery_timeout=20.0,
    success_threshold=2,
)

# Webhook delivery — very tolerant
webhook_breaker = CircuitBreaker(
    "webhooks",
    failure_threshold=10,
    recovery_timeout=60.0,
    success_threshold=5,
)


def get_all_breaker_status() -> list:
    """Get status of all circuit breakers."""
    return [
        inference_breaker.get_status(),
        database_breaker.get_status(),
        vector_breaker.get_status(),
        webhook_breaker.get_status(),
    ]
