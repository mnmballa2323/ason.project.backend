import os

# --- Allowed Origins ---
ALLOWED_ORIGINS = [
    "http://localhost:3001",
    "http://localhost:5173",
    "https://qwen.libertycenter.one",
]

# --- Input Validation Limits ---
MAX_CLAIMS_PER_REQUEST = 50
MAX_CLAIM_LENGTH = 5000  # characters
MAX_REQUEST_BODY_BYTES = 1_048_576  # 1 MB

# --- Rate Limiting (Tenant-Scoped) ---
RATE_LIMIT_MAX = int(os.getenv("ASON_RATE_LIMIT_MAX", "100"))  # requests per window
RATE_LIMIT_WINDOW = int(os.getenv("ASON_RATE_LIMIT_WINDOW", "60"))  # seconds

# --- Data Retention ---
JOB_RETENTION_HOURS = int(os.getenv("JOB_RETENTION_HOURS", "168"))  # 7 days default
AUDIT_RETENTION_HOURS = int(os.getenv("AUDIT_RETENTION_HOURS", "2160"))  # 90 days default

# --- External Services ---
POSTGRES_URL = os.getenv("POSTGRES_URL", "")
INFERENCE_URL = os.getenv("INFERENCE_URL", "http://ason-inference:8000/generate")
INFERENCE_TIMEOUT = int(os.getenv("INFERENCE_TIMEOUT", "60"))

# --- Security ---
HMAC_SECRET = os.getenv("HMAC_SECRET", "change_me_in_prod")
SERVER_JURISDICTION_STR = os.getenv("SERVER_JURISDICTION", "US")
_raw_allowlist = os.getenv("ASON_IP_ALLOWLIST", "")  # Comma-separated CIDRs
IP_ALLOWLIST_CIDRS = [cidr.strip() for cidr in _raw_allowlist.split(",") if cidr.strip()]

# --- Webhook Validation ---
ALLOWED_WEBHOOK_DOMAINS = {"localhost", "libertycenter.one"}
class config:
    @staticmethod
    def validate():
        warnings = []
        if HMAC_SECRET == "change_me_in_prod":
            warnings.append("HMAC_SECRET is using default value!")
        if not POSTGRES_URL:
             warnings.append("POSTGRES_URL not set — using in-memory job store (non-persistent)")
        return warnings
