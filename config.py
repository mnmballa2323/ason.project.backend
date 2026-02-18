"""
Centralized Configuration — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Validated with Pydantic Settings. All config via environment variables.
"""

import os
from typing import List, Optional


class AsonConfig:
    """
    Centralized configuration with environment variable validation.
    All values have sensible defaults for local development.
    In production, set via K8s ConfigMap / Docker env.
    """

    # --- Application ---
    APP_NAME: str = "Ason Verification Orchestrator"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = os.getenv("ASON_ENV", "development")
    DEBUG: bool = os.getenv("ASON_DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("ASON_LOG_LEVEL", "INFO")

    # --- Server ---
    HOST: str = os.getenv("ASON_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("ASON_PORT", "8000"))
    WORKERS: int = int(os.getenv("ASON_WORKERS", "1"))
    MAX_CONCURRENCY: int = int(os.getenv("ASON_MAX_CONCURRENCY", "100"))

    # --- Database (PostgreSQL) ---
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "")
    POSTGRES_POOL_MIN: int = int(os.getenv("POSTGRES_POOL_MIN", "2"))
    POSTGRES_POOL_MAX: int = int(os.getenv("POSTGRES_POOL_MAX", "10"))
    POSTGRES_TIMEOUT: int = int(os.getenv("POSTGRES_TIMEOUT", "30"))

    # --- Inference (Self-Hosted vLLM) ---
    INFERENCE_URL: str = os.getenv("INFERENCE_URL", "http://ason-inference:8000/generate")
    INFERENCE_TIMEOUT: int = int(os.getenv("INFERENCE_TIMEOUT", "120"))
    INFERENCE_MAX_RETRIES: int = int(os.getenv("INFERENCE_MAX_RETRIES", "3"))

    # --- Model ---
    MODEL_NAME: str = os.getenv("ASON_MODEL_NAME", "Qwen/Qwen2-72B-Instruct")
    MODEL_VERSION: str = os.getenv("ASON_MODEL_VERSION", "2.0.0")
    MODEL_TEMPERATURE: float = float(os.getenv("ASON_MODEL_TEMPERATURE", "0.0"))
    MODEL_SEED: int = int(os.getenv("ASON_MODEL_SEED", "42"))

    # --- Embeddings (Self-Hosted) ---
    EMBEDDING_MODEL: str = os.getenv("ASON_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

    # --- Vector Store (Milvus) ---
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "milvus-standalone")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))

    # --- Security ---
    CORS_ORIGINS: List[str] = os.getenv(
        "ASON_CORS_ORIGINS",
        "http://localhost:3001,http://localhost:5173,https://qwen.libertycenter.one"
    ).split(",")
    RATE_LIMIT_MAX: int = int(os.getenv("ASON_RATE_LIMIT_MAX", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("ASON_RATE_LIMIT_WINDOW", "60"))
    JWT_ISSUER: str = os.getenv("ASON_JWT_ISSUER", "keycloak.libertycenter.one")

    # --- Input Validation ---
    MAX_CLAIMS_PER_REQUEST: int = int(os.getenv("ASON_MAX_CLAIMS", "50"))
    MAX_CLAIM_LENGTH: int = int(os.getenv("ASON_MAX_CLAIM_LENGTH", "5000"))
    MAX_REQUEST_BODY_BYTES: int = int(os.getenv("ASON_MAX_BODY_BYTES", "1048576"))
    MAX_BATCH_SIZE: int = int(os.getenv("ASON_MAX_BATCH_SIZE", "20"))

    # --- Monitoring ---
    JAEGER_ENDPOINT: str = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")
    PROMETHEUS_ENABLED: bool = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"

    # --- mTLS ---
    TLS_ENABLED: bool = os.getenv("ASON_TLS_ENABLED", "false").lower() == "true"
    TLS_CERT_PATH: str = os.getenv("ASON_TLS_CERT", "/etc/ason-certs/server.crt")
    TLS_KEY_PATH: str = os.getenv("ASON_TLS_KEY", "/etc/ason-certs/server.key")
    TLS_CA_PATH: str = os.getenv("ASON_TLS_CA", "/etc/ason-certs/ca.crt")

    # --- Deployment ---
    DEPLOYMENT_NAME: str = "Liberty Center One (Private OpenStack)"
    DEPLOYMENT_REGION: str = os.getenv("ASON_REGION", "LC1-East")

    def validate(self) -> List[str]:
        """Validate critical configuration. Returns list of warnings."""
        warnings = []
        if not self.POSTGRES_URL:
            warnings.append("POSTGRES_URL not set — using in-memory job store")
        if self.ENVIRONMENT == "production" and self.DEBUG:
            warnings.append("DEBUG=true in production — THIS IS DANGEROUS")
        if self.ENVIRONMENT == "production" and not self.TLS_ENABLED:
            warnings.append("TLS disabled in production — mTLS should be enabled")
        if self.MODEL_TEMPERATURE != 0.0:
            warnings.append(f"Model temperature={self.MODEL_TEMPERATURE} — determinism compromised")
        return warnings

    def to_dict(self) -> dict:
        """Export config as dict (redacted for security)."""
        return {
            "app": self.APP_NAME,
            "version": self.APP_VERSION,
            "environment": self.ENVIRONMENT,
            "debug": self.DEBUG,
            "inference_url": self.INFERENCE_URL,
            "model": self.MODEL_NAME,
            "embedding": self.EMBEDDING_MODEL,
            "postgres": "connected" if self.POSTGRES_URL else "in-memory",
            "tls": "enabled" if self.TLS_ENABLED else "disabled",
            "region": self.DEPLOYMENT_REGION,
            "rate_limit": f"{self.RATE_LIMIT_MAX}/{self.RATE_LIMIT_WINDOW}s",
        }


# Global singleton
config = AsonConfig()
