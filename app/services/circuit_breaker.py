import time
import requests
import logging

logger = logging.getLogger("qwen.orchestrator")

class CircuitBreakerOpen(Exception):
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                logger.info("Circuit Breaker probe (HALF-OPEN)...")
            else:
                raise CircuitBreakerOpen("Circuit is OPEN")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF-OPEN":
                self.state = "CLOSED"
                self.failures = 0
                logger.info("Circuit Breaker recovered (CLOSED)")
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"Circuit Breaker tripped (OPEN) after {self.failures} failures")
            raise e

# Simple singleton or factory usage if needed
# For now, we just expose the class
