"""
Deception Technology — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Honeypots, honeytokens, and canary traps for detecting
internal threats, lateral movement, and data exfiltration.

NASDAQ 100 Requirement: Active defense with deception-in-depth.
"""

import hashlib
import logging
import os
import threading
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("qwen.deception")


class DeceptionType(str, Enum):
    HONEYTOKEN = "honeytoken"           # Fake credentials / API keys
    HONEYPOT_API = "honeypot_api"       # Fake API endpoints
    HONEYPOT_FILE = "honeypot_file"     # Canary files (trigger on access)
    HONEYPOT_DB = "honeypot_db_record"  # Fake database records
    CANARY_DNS = "canary_dns"           # DNS canary tokens
    CANARY_DOC = "canary_document"      # Tracked documents
    DECOY_SERVICE = "decoy_service"     # Fake microservices
    BREADCRUMB = "breadcrumb"           # Deliberate trail to honeypot


class TripwireStatus(str, Enum):
    ARMED = "armed"
    TRIGGERED = "triggered"
    DISABLED = "disabled"


class DeceptionAsset:
    """A deception asset deployed within the platform."""
    def __init__(self, asset_id, deception_type, name, location,
                 description="", bait_value=""):
        self.asset_id = asset_id
        self.deception_type = deception_type
        self.name = name
        self.location = location  # Where the trap is placed
        self.description = description
        self.bait_value = bait_value  # The fake credential/key/data
        self.status = TripwireStatus.ARMED
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.trips: List[Dict] = []
        self.canary_token = hashlib.sha256(
            f"canary-{asset_id}-{os.urandom(8).hex()}".encode()
        ).hexdigest()[:24]

    def trigger(self, accessor, source_ip="", context=None):
        """Record a trip event — someone touched the trap."""
        trip = {
            "accessor": accessor,
            "source_ip": source_ip,
            "context": context or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "asset_id": self.asset_id,
            "deception_type": self.deception_type.value,
        }
        self.trips.append(trip)
        self.status = TripwireStatus.TRIGGERED
        logger.critical(
            f"DECEPTION TRIGGERED [{self.deception_type.value}]: "
            f"'{self.name}' accessed by {accessor} from {source_ip}"
        )
        return trip

    def to_dict(self):
        return {
            "asset_id": self.asset_id,
            "type": self.deception_type.value,
            "name": self.name,
            "location": self.location,
            "status": self.status.value,
            "trip_count": len(self.trips),
            "canary_token": self.canary_token,
            "created_at": self.created_at,
        }


class DeceptionFramework:
    """Manages honeypots, honeytokens, and canary traps."""

    def __init__(self):
        self._assets: Dict[str, DeceptionAsset] = {}
        self._trips: List[Dict] = []
        self._lock = threading.Lock()
        self._counter = 0
        self._deploy_defaults()

    def _deploy_defaults(self):
        """Deploy default deception assets across the platform."""

        # Honeytokens — fake credentials seeded in config
        self._deploy(DeceptionType.HONEYTOKEN,
                     "Admin API Key (Fake)", "config/api_keys.env",
                     "Fake admin API key that triggers alert on use",
                     "ason_ak_FAKE_Xj9mK2pL4qR7sT0vWyBz")
        self._deploy(DeceptionType.HONEYTOKEN,
                     "AWS Root Key (Fake)", "config/cloud.env",
                     "Fake AWS key triggers immediate containment",
                     "AKIAIOSFODNN7DECOY01")
        self._deploy(DeceptionType.HONEYTOKEN,
                     "Database Password (Fake)", "config/db.env",
                     "Fake DB password monitored for use",
                     "p@ssw0rd_CANARY_d3c0y_2026!")

        # Honeypot API endpoints
        self._deploy(DeceptionType.HONEYPOT_API,
                     "/api/v1/admin/backup-keys", "/api/v1/admin/backup-keys",
                     "Fake admin endpoint — any access is an attack indicator")
        self._deploy(DeceptionType.HONEYPOT_API,
                     "/api/v1/internal/debug", "/api/v1/internal/debug",
                     "Debug endpoint that doesn't exist — access = recon")
        self._deploy(DeceptionType.HONEYPOT_API,
                     "/.env", "/.env",
                     "Fake .env file access — common attack vector")
        self._deploy(DeceptionType.HONEYPOT_API,
                     "/wp-admin", "/wp-admin",
                     "WordPress admin path — never should be accessed")

        # Canary files
        self._deploy(DeceptionType.HONEYPOT_FILE,
                     "credentials.bak", "/data/backups/credentials.bak",
                     "Canary backup file — access indicates insider threat")
        self._deploy(DeceptionType.HONEYPOT_FILE,
                     "private_keys.pem", "/config/private_keys.pem",
                     "Fake key file — access triggers immediate alert")

        # Canary database records
        self._deploy(DeceptionType.HONEYPOT_DB,
                     "canary_user_ceo@qwen.internal", "users table",
                     "Fake CEO user record — access triggers investigation")
        self._deploy(DeceptionType.HONEYPOT_DB,
                     "canary_verification_CLASSIFIED", "verifications table",
                     "Fake classified verification — access = unauthorized")

        # Decoy services
        self._deploy(DeceptionType.DECOY_SERVICE,
                     "legacy-auth.qwen.internal:8443", "service mesh",
                     "Fake legacy auth service — connection = lateral movement")
        self._deploy(DeceptionType.DECOY_SERVICE,
                     "vault.qwen.internal:8200", "service mesh",
                     "Fake Vault service — connection = credential theft attempt")

        # Breadcrumbs leading to honeypots
        self._deploy(DeceptionType.BREADCRUMB,
                     "server-config.txt", "/tmp/server-config.txt",
                     "Planted config with fake internal IPs pointing to honeypots")
        self._deploy(DeceptionType.BREADCRUMB,
                     ".ssh/known_hosts", "/home/qwen/.ssh/known_hosts",
                     "Fake SSH hosts pointing to decoy services")

    def _deploy(self, dtype, name, location, description="", bait=""):
        with self._lock:
            self._counter += 1
            asset_id = f"DEC-{self._counter:06d}"
        asset = DeceptionAsset(asset_id, dtype, name, location, description, bait)
        self._assets[asset_id] = asset
        return asset

    def check_honeytoken(self, value: str) -> Optional[Dict]:
        """Check if a value matches any deployed honeytoken."""
        for asset in self._assets.values():
            if (asset.deception_type == DeceptionType.HONEYTOKEN and
                    asset.bait_value and value == asset.bait_value):
                return asset.trigger("honeytoken_check", context={"matched": True})
        return None

    def check_endpoint(self, path: str, source_ip: str = "",
                       actor: str = "") -> Optional[Dict]:
        """Check if a request hits a honeypot endpoint."""
        for asset in self._assets.values():
            if (asset.deception_type == DeceptionType.HONEYPOT_API and
                    asset.location == path):
                return asset.trigger(actor or "unknown", source_ip,
                                    {"path": path})
        return None

    def report_file_access(self, filepath: str, accessor: str,
                           source_ip: str = "") -> Optional[Dict]:
        """Report file access for canary detection."""
        for asset in self._assets.values():
            if asset.deception_type == DeceptionType.HONEYPOT_FILE:
                if asset.location in filepath or asset.name in filepath:
                    return asset.trigger(accessor, source_ip,
                                        {"filepath": filepath})
        return None

    def get_triggered_assets(self) -> List[Dict]:
        return [a.to_dict() for a in self._assets.values()
                if a.status == TripwireStatus.TRIGGERED]

    def get_all_trips(self, limit=100) -> List[Dict]:
        all_trips = []
        for asset in self._assets.values():
            all_trips.extend(asset.trips)
        all_trips.sort(key=lambda t: t["timestamp"], reverse=True)
        return all_trips[:limit]

    def get_stats(self) -> Dict:
        by_type = {}
        for a in self._assets.values():
            t = a.deception_type.value
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "total_assets": len(self._assets),
            "armed": sum(1 for a in self._assets.values()
                         if a.status == TripwireStatus.ARMED),
            "triggered": sum(1 for a in self._assets.values()
                             if a.status == TripwireStatus.TRIGGERED),
            "total_trips": sum(len(a.trips) for a in self._assets.values()),
            "by_type": by_type,
            "deception_coverage": [
                "honeytoken credentials (3)",
                "honeypot API endpoints (4)",
                "canary files (2)",
                "canary DB records (2)",
                "decoy services (2)",
                "breadcrumbs (2)",
            ],
        }

deception_framework = DeceptionFramework()
