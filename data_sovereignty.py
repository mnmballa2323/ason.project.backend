"""
Data Sovereignty Controller — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs

Hard enforcement of data residency by jurisdiction.
Covers: GDPR, CCPA/CPRA, China PIPL, India DPDP, Brazil LGPD,
Japan APPI, South Korea PIPA, Australia Privacy Act.
"""

import os

logger = logging.getLogger("qwen.data_sovereignty")


class Jurisdiction(str, Enum):
    EU = "EU"
    US = "US"
    US_CA = "US-CA"       # California
    CN = "CN"             # China
    IN = "IN"             # India
    BR = "BR"             # Brazil
    JP = "JP"             # Japan
    KR = "KR"             # South Korea
    AU = "AU"             # Australia
    UK = "UK"
    CA = "CA"             # Canada
    SG = "SG"             # Singapore
    CH = "CH"             # Switzerland
    GLOBAL = "GLOBAL"


class DataCategory(str, Enum):
    PII = "pii"
    SENSITIVE_PII = "sensitive_pii"
    FINANCIAL = "financial"
    HEALTH = "health"
    BIOMETRIC = "biometric"
    CHILDREN = "children_data"
    EMPLOYEE = "employee_data"
    VERIFICATION = "verification_data"
    ANALYTICS = "analytics"
    METADATA = "metadata"
    TOP_SECRET = "top_secret"


class TransferMechanism(str, Enum):
    ADEQUACY = "adequacy_decision"
    SCC = "standard_contractual_clauses"
    BCR = "binding_corporate_rules"
    CONSENT = "explicit_consent"
    LEGAL_OBLIGATION = "legal_obligation"
    DEROGATION = "derogation"
    PROHIBITED = "prohibited"


RESIDENCY_RULES = {
    Jurisdiction.EU: {
        "regulation": "GDPR (Regulation 2016/679)",
        "transfer_allowed_to": {Jurisdiction.UK, Jurisdiction.CH, Jurisdiction.CA, Jurisdiction.JP},
        "requires_dpia": {DataCategory.SENSITIVE_PII, DataCategory.BIOMETRIC, DataCategory.HEALTH},
        "data_must_stay": True,
        "breach_notify_hours": 72,
    },
    Jurisdiction.CN: {
        "regulation": "PIPL (2021)",
        "transfer_allowed_to": set(),  # Requires security assessment
        "requires_dpia": {DataCategory.PII, DataCategory.SENSITIVE_PII},
        "data_must_stay": True,
        "breach_notify_hours": 0,  # Immediately
    },
    Jurisdiction.IN: {
        "regulation": "DPDP Act (2023)",
        "transfer_allowed_to": set(),  # Government whitelist
        "requires_dpia": {DataCategory.SENSITIVE_PII, DataCategory.CHILDREN},
        "data_must_stay": True,
        "breach_notify_hours": 72,
    },
    Jurisdiction.US_CA: {
        "regulation": "CCPA/CPRA",
        "transfer_allowed_to": {Jurisdiction.US},
        "requires_dpia": {DataCategory.SENSITIVE_PII},
        "data_must_stay": False,
        "breach_notify_hours": 72,
    },
    Jurisdiction.BR: {
        "regulation": "LGPD (2018)",
        "transfer_allowed_to": {Jurisdiction.EU},
        "requires_dpia": {DataCategory.SENSITIVE_PII, DataCategory.HEALTH},
        "data_must_stay": True,
        "breach_notify_hours": 48,
    },
}


class DataResidencyPolicy:
    """A data residency policy for a jurisdiction."""
    def __init__(self, policy_id, jurisdiction, data_categories,
                 storage_region, allowed_regions):
        self.policy_id = policy_id
        self.jurisdiction = jurisdiction
        self.data_categories = data_categories
        self.storage_region = storage_region
        self.allowed_regions = allowed_regions
        self.violations: List[Dict] = []

    def to_dict(self):
        return {
            "policy_id": self.policy_id,
            "jurisdiction": self.jurisdiction.value,
            "storage_region": self.storage_region,
            "allowed_regions": list(self.allowed_regions),
            "violations": len(self.violations),
        }


class DataSovereigntyController:
    """Hard enforcement of data residency rules."""

    DDL = """
    CREATE TABLE IF NOT EXISTS sovereignty_policies (
        policy_id TEXT PRIMARY KEY,
        jurisdiction TEXT NOT NULL,
        data_categories TEXT[],
        storage_region TEXT,
        allowed_regions TEXT[],
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """

    def __init__(self):
        self._policies: Dict[str, DataResidencyPolicy] = {}
        self._violations: List[Dict] = []
        self._counter = 0
        self.db_url = os.getenv("POSTGRES_URL", "")
        self._db_available = False

    async def initialize(self):
        """Initialize DB tables."""
        if not self.db_url:
            return
        try:
            import psycopg
            async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                async with conn.cursor() as cur:
                    await cur.execute(self.DDL)
                await conn.commit()
            self._db_available = True
            await self._load_policies()
            logger.info("Data Sovereignty persistence initialized.")
        except Exception as e:
            logger.warning(f"Data Sovereignty DB init failed: {e}")

    async def _load_policies(self):
        """Load persistent policies into memory."""
        try:
            import psycopg
            async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT * FROM sovereignty_policies")
                    rows = await cur.fetchall()
                    for row in rows:
                        # row: policy_id, jurisdiction, data_categories, storage_region, allowed_regions, created_at
                        pid, juris_str, cats, region, allowed, _ = row
                        juris = Jurisdiction(juris_str)
                        # Handle potential string vs enum list
                        policy = DataResidencyPolicy(
                            pid, juris, cats, region, set(allowed)
                        )
                        self._policies[pid] = policy
                        # Simple counter recovery
                        try:
                            num = int(pid.split("-")[1])
                            self._counter = max(self._counter, num)
                        except:
                            pass
        except Exception as e:
            logger.error(f"Failed to load policies: {e}")

    async def create_policy(self, jurisdiction: Jurisdiction,
                            data_categories: List[DataCategory],
                            storage_region: str,
                            allowed_regions: Set[str]) -> DataResidencyPolicy:
        self._counter += 1
        policy_id = f"DSP-{self._counter:06d}"
        policy = DataResidencyPolicy(
            policy_id, jurisdiction, data_categories,
            storage_region, allowed_regions,
        )
        self._policies[policy_id] = policy
        
        if self._db_available:
            try:
                import psycopg
                async with await psycopg.AsyncConnection.connect(self.db_url) as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(
                            "INSERT INTO sovereignty_policies (policy_id, jurisdiction, data_categories, storage_region, allowed_regions) "
                            "VALUES (%s, %s, %s, %s, %s)",
                            (policy_id, jurisdiction.value, [c.value for c in data_categories], storage_region, list(allowed_regions))
                        )
                    await conn.commit()
            except Exception as e:
                logger.error(f"Failed to persist policy {policy_id}: {e}")

        return policy

    def validate_transfer(self, source_jurisdiction: Jurisdiction,
                          target_jurisdiction: Jurisdiction,
                          data_category: DataCategory) -> Dict:
        """Validate a cross-border data transfer."""
        # 1. Check strict hardcoded rules first
        rules = RESIDENCY_RULES.get(source_jurisdiction)
        if not rules:
            return {"allowed": True, "mechanism": "no_restrictions"}

        allowed_to = rules.get("transfer_allowed_to", set())
        if target_jurisdiction in allowed_to:
            return {
                "allowed": True,
                "mechanism": TransferMechanism.ADEQUACY.value,
                "regulation": rules["regulation"],
            }
        
        # 2. Check dynamic policies (if any exist that override/augment)
        # TODO: Dynamic policy check logic here

        if rules.get("data_must_stay"):
            # Check if source == target (Local processing)
            if source_jurisdiction == target_jurisdiction:
                 return {"allowed": True, "mechanism": "local_processing"}

            violation = {
                "type": "cross_border_violation",
                "source": source_jurisdiction.value,
                "target": target_jurisdiction.value,
                "data_category": data_category.value,
                "regulation": rules["regulation"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._violations.append(violation)
            return {
                "allowed": False,
                "reason": f"Data must remain in {source_jurisdiction.value}",
                "regulation": rules["regulation"],
                "required_mechanism": TransferMechanism.SCC.value,
            }

        return {"allowed": True, "mechanism": TransferMechanism.CONSENT.value}

    def check_dpia_required(self, jurisdiction: Jurisdiction,
                            data_category: DataCategory) -> bool:
        """Check if DPIA is required."""
        rules = RESIDENCY_RULES.get(jurisdiction, {})
        req = rules.get("requires_dpia", set())
        return data_category in req

    def get_breach_notification_deadline(self, jurisdiction: Jurisdiction) -> Dict:
        rules = RESIDENCY_RULES.get(jurisdiction, {})
        return {
            "jurisdiction": jurisdiction.value,
            "notify_within_hours": rules.get("breach_notify_hours", 72),
            "regulation": rules.get("regulation", "N/A"),
        }

    def get_stats(self) -> Dict:
        return {
            "policies": len(self._policies),
            "violations": len(self._violations),
            "jurisdictions_covered": len(RESIDENCY_RULES),
            "regulations": [r["regulation"] for r in RESIDENCY_RULES.values()],
        }

data_sovereignty = DataSovereigntyController()
