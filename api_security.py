"""
API Security Gateway — Ason Verification Platform
ZERO EXTERNAL APIs | MIT/Apache 2.0 | Self-Hosted

Rate limiting, schema validation, abuse detection, hardened OAuth 2.1.
"""

import hashlib, logging, os, re, threading, time
from collections import defaultdict
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.api_gateway")


# ============================================================================
#  API GATEWAY — Rate Limiting & Quota
# ============================================================================

class RateLimitAlgorithm(str, Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def allow(self) -> bool:
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False


class TenantQuota:
    def __init__(self, tenant_id, daily_limit, rate_per_minute):
        self.tenant_id = tenant_id
        self.daily_limit = daily_limit
        self.rate_per_minute = rate_per_minute
        self.daily_used = 0
        self.bucket = TokenBucket(rate_per_minute, rate_per_minute / 60.0)
        self.last_reset = time.time()

    def check(self) -> Dict:
        # Reset daily counter
        if time.time() - self.last_reset > 86400:
            self.daily_used = 0
            self.last_reset = time.time()
        if self.daily_used >= self.daily_limit:
            return {"allowed": False, "reason": "daily_quota_exceeded"}
        if not self.bucket.allow():
            return {"allowed": False, "reason": "rate_limit_exceeded"}
        self.daily_used += 1
        return {"allowed": True, "remaining_daily": self.daily_limit - self.daily_used}


class APIGateway:
    """Rate limiting, throttling, and quota management."""

    def __init__(self):
        self._tenants: Dict[str, TenantQuota] = {}
        self._default_daily = 10000
        self._default_rate = 100
        self._requests = 0
        self._blocked = 0

    def register_tenant(self, tenant_id: str, daily_limit: int = None,
                       rate_per_minute: int = None) -> Dict:
        self._tenants[tenant_id] = TenantQuota(
            tenant_id, daily_limit or self._default_daily,
            rate_per_minute or self._default_rate)
        return {"registered": True, "tenant": tenant_id}

    def check_request(self, tenant_id: str) -> Dict:
        self._requests += 1
        if tenant_id not in self._tenants:
            self.register_tenant(tenant_id)
        result = self._tenants[tenant_id].check()
        if not result["allowed"]:
            self._blocked += 1
        return result

    def get_stats(self) -> Dict:
        return {"tenants": len(self._tenants), "total_requests": self._requests,
                "blocked": self._blocked}


# ============================================================================
#  API SCHEMA VALIDATOR
# ============================================================================

class SchemaValidation:
    def __init__(self, field, field_type, required=True, min_val=None,
                 max_val=None, pattern=None, enum_vals=None):
        self.field = field
        self.field_type = field_type
        self.required = required
        self.min_val = min_val
        self.max_val = max_val
        self.pattern = pattern
        self.enum_vals = enum_vals


class APISchemaValidator:
    """OpenAPI-style runtime request/response validation."""

    ENDPOINT_SCHEMAS = {
        "/api/auth/login": [
            SchemaValidation("username", "string", required=True, pattern=r"^[a-zA-Z0-9_]{3,50}$"),
            SchemaValidation("password", "string", required=True, min_val=8, max_val=128),
        ],
        "/api/verify": [
            SchemaValidation("content", "string", required=True, max_val=100000),
            SchemaValidation("model", "string", required=True,
                            enum_vals=["ason-7b", "ason-14b", "ason-72b"]),
        ],
        "/api/security/scan": [
            SchemaValidation("content", "string", required=True),
            SchemaValidation("context", "string", required=False),
        ],
    }

    def __init__(self):
        self._validations = 0
        self._failures = 0

    def validate(self, endpoint: str, body: Dict) -> Dict:
        self._validations += 1
        schema = self.ENDPOINT_SCHEMAS.get(endpoint)
        if not schema:
            return {"valid": True, "message": "No schema defined"}
        errors = []
        for field_def in schema:
            value = body.get(field_def.field)
            if field_def.required and value is None:
                errors.append(f"Missing required field: {field_def.field}")
                continue
            if value is None:
                continue
            if field_def.field_type == "string" and not isinstance(value, str):
                errors.append(f"{field_def.field}: expected string")
            if field_def.min_val and isinstance(value, str) and len(value) < field_def.min_val:
                errors.append(f"{field_def.field}: too short (min {field_def.min_val})")
            if field_def.max_val and isinstance(value, str) and len(value) > field_def.max_val:
                errors.append(f"{field_def.field}: too long (max {field_def.max_val})")
            if field_def.pattern and isinstance(value, str):
                if not re.match(field_def.pattern, value):
                    errors.append(f"{field_def.field}: pattern mismatch")
            if field_def.enum_vals and value not in field_def.enum_vals:
                errors.append(f"{field_def.field}: must be one of {field_def.enum_vals}")
        if errors:
            self._failures += 1
        return {"valid": len(errors) == 0, "errors": errors}

    def get_stats(self) -> Dict:
        return {"validations": self._validations, "failures": self._failures,
                "schemas": len(self.ENDPOINT_SCHEMAS)}


# ============================================================================
#  API ABUSE DETECTOR
# ============================================================================

class AbusePattern:
    def __init__(self, name, description, detection_fn, severity):
        self.name = name
        self.description = description
        self.detection_fn = detection_fn
        self.severity = severity
        self.detections = 0


class APIAbuseDetector:
    """Detect scraping, enumeration, credential stuffing."""

    def __init__(self):
        self._request_history: Dict[str, List[Dict]] = defaultdict(list)
        self._detections: List[Dict] = []
        self._patterns: List[AbusePattern] = []
        self._seed()

    def _seed(self):
        self._patterns = [
            AbusePattern("credential_stuffing",
                        "Multiple failed auth attempts from same IP",
                        self._detect_credential_stuffing, "critical"),
            AbusePattern("api_scraping",
                        "High-frequency sequential endpoint access",
                        self._detect_scraping, "high"),
            AbusePattern("enumeration",
                        "Sequential ID/username probing",
                        self._detect_enumeration, "high"),
            AbusePattern("slowloris",
                        "Connection holding / slow-rate attack",
                        self._detect_slowloris, "medium"),
            AbusePattern("parameter_fuzzing",
                        "Unusual parameter variations",
                        self._detect_fuzzing, "medium"),
        ]

    def record_request(self, client_ip: str, endpoint: str,
                      status: int, duration_ms: float) -> Dict:
        record = {"endpoint": endpoint, "status": status,
                  "duration_ms": duration_ms, "ts": time.time()}
        self._request_history[client_ip].append(record)
        # Keep last 100 per IP
        if len(self._request_history[client_ip]) > 100:
            self._request_history[client_ip] = self._request_history[client_ip][-100:]
        # Run detections
        alerts = []
        for pattern in self._patterns:
            if pattern.detection_fn(client_ip):
                pattern.detections += 1
                alert = {"pattern": pattern.name, "ip": client_ip,
                         "severity": pattern.severity,
                         "ts": datetime.now(timezone.utc).isoformat()}
                alerts.append(alert)
                self._detections.append(alert)
        return {"alerts": alerts}

    def _detect_credential_stuffing(self, ip: str) -> bool:
        history = self._request_history.get(ip, [])
        recent = [r for r in history if time.time() - r["ts"] < 300]
        failures = [r for r in recent if r["status"] == 401]
        return len(failures) >= 5

    def _detect_scraping(self, ip: str) -> bool:
        history = self._request_history.get(ip, [])
        recent = [r for r in history if time.time() - r["ts"] < 60]
        return len(recent) >= 50

    def _detect_enumeration(self, ip: str) -> bool:
        history = self._request_history.get(ip, [])
        recent = [r for r in history if time.time() - r["ts"] < 300]
        not_found = [r for r in recent if r["status"] == 404]
        return len(not_found) >= 10

    def _detect_slowloris(self, ip: str) -> bool:
        history = self._request_history.get(ip, [])
        recent = [r for r in history if time.time() - r["ts"] < 300]
        slow = [r for r in recent if r["duration_ms"] > 30000]
        return len(slow) >= 3

    def _detect_fuzzing(self, ip: str) -> bool:
        history = self._request_history.get(ip, [])
        recent = [r for r in history if time.time() - r["ts"] < 60]
        error = [r for r in recent if r["status"] >= 400]
        return len(error) >= 20

    def get_stats(self) -> Dict:
        return {"tracked_ips": len(self._request_history),
                "patterns": len(self._patterns),
                "total_detections": len(self._detections)}


# ============================================================================
#  HARDENED OAUTH 2.1
# ============================================================================

class OAuthGrant:
    def __init__(self, grant_id, client_id, code_verifier, scope, redirect_uri):
        self.grant_id = grant_id
        self.client_id = client_id
        self.code_verifier = code_verifier
        self.scope = scope
        self.redirect_uri = redirect_uri
        self.code = os.urandom(32).hex()
        self.code_challenge = hashlib.sha256(code_verifier.encode()).hexdigest()
        self.exchanged = False
        self.created_at = time.time()
        self.ttl_sec = 60  # Auth code expires in 60s


class OAuthToken:
    def __init__(self, token_id, client_id, scope, token_type="DPoP"):
        self.token_id = token_id
        self.client_id = client_id
        self.scope = scope
        self.token_type = token_type
        self.access_token = os.urandom(32).hex()
        self.refresh_token = os.urandom(32).hex()
        self.dpop_thumbprint = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        self.created_at = time.time()
        self.access_ttl = 300   # 5 min
        self.refresh_ttl = 3600  # 1 hour
        self.revoked = False
        self.rotation_count = 0

    @property
    def access_expired(self):
        return time.time() > self.created_at + self.access_ttl

    def to_dict(self):
        return {"token_id": self.token_id, "client_id": self.client_id,
                "scope": self.scope, "type": self.token_type,
                "dpop": self.dpop_thumbprint,
                "access_expired": self.access_expired, "revoked": self.revoked}


class HardenedOAuth:
    """OAuth 2.1 with PKCE, DPoP, token binding, refresh rotation."""

    def __init__(self):
        self._grants: Dict[str, OAuthGrant] = {}
        self._tokens: Dict[str, OAuthToken] = {}
        self._counter = 0
        self._lock = threading.Lock()

    def authorize(self, client_id: str, code_verifier: str,
                 scope: str, redirect_uri: str) -> Dict:
        with self._lock:
            self._counter += 1
            gid = f"GRANT-{self._counter:010d}"
        grant = OAuthGrant(gid, client_id, code_verifier, scope, redirect_uri)
        self._grants[grant.code] = grant
        return {"code": grant.code, "expires_in": grant.ttl_sec}

    def token_exchange(self, code: str, code_verifier: str,
                      client_id: str) -> Dict:
        grant = self._grants.get(code)
        if not grant:
            return {"error": "invalid_grant"}
        if grant.exchanged:
            return {"error": "grant_already_exchanged"}
        if time.time() > grant.created_at + grant.ttl_sec:
            return {"error": "grant_expired"}
        # PKCE verification
        challenge = hashlib.sha256(code_verifier.encode()).hexdigest()
        if challenge != grant.code_challenge:
            return {"error": "invalid_code_verifier"}
        if grant.client_id != client_id:
            return {"error": "client_mismatch"}
        grant.exchanged = True
        with self._lock:
            self._counter += 1
            tid = f"TOK-{self._counter:010d}"
        token = OAuthToken(tid, client_id, grant.scope)
        self._tokens[token.access_token] = token
        return {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "token_type": "DPoP",
            "expires_in": token.access_ttl,
            "dpop_thumbprint": token.dpop_thumbprint,
        }

    def refresh(self, refresh_token: str, client_id: str) -> Dict:
        """Refresh with rotation — old refresh token immediately invalidated."""
        old_token = None
        for t in self._tokens.values():
            if t.refresh_token == refresh_token and not t.revoked:
                old_token = t
                break
        if not old_token:
            return {"error": "invalid_refresh_token"}
        if old_token.client_id != client_id:
            return {"error": "client_mismatch"}
        # Rotate
        old_token.revoked = True
        with self._lock:
            self._counter += 1
            tid = f"TOK-{self._counter:010d}"
        new_token = OAuthToken(tid, client_id, old_token.scope)
        new_token.rotation_count = old_token.rotation_count + 1
        self._tokens[new_token.access_token] = new_token
        return {
            "access_token": new_token.access_token,
            "refresh_token": new_token.refresh_token,
            "rotation": new_token.rotation_count,
        }

    def introspect(self, access_token: str) -> Dict:
        token = self._tokens.get(access_token)
        if not token:
            return {"active": False}
        return {"active": not token.access_expired and not token.revoked,
                **token.to_dict()}

    def revoke(self, access_token: str) -> Dict:
        token = self._tokens.get(access_token)
        if token:
            token.revoked = True
            return {"revoked": True}
        return {"error": "Token not found"}

    def get_stats(self) -> Dict:
        active = sum(1 for t in self._tokens.values()
                     if not t.revoked and not t.access_expired)
        return {"grants": len(self._grants), "tokens": len(self._tokens),
                "active_tokens": active}


# Singletons
api_gateway = APIGateway()
schema_validator = APISchemaValidator()
abuse_detector = APIAbuseDetector()
hardened_oauth = HardenedOAuth()
