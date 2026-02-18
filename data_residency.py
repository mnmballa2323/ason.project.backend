"""
Data Residency Controls — Ason Verification Platform
Liberty Center One — ZERO EXTERNAL APIs
Region-pinning for GDPR, data sovereignty, and compliance.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("qwen.residency")


# ============================================================================
#  DATA REGIONS
# ============================================================================

class DataRegion(str, Enum):
    # Americas
    US_EAST = "us-east-1"
    US_WEST = "us-west-2"
    US_GOV = "us-gov-west-1"
    CA_CENTRAL = "ca-central-1"
    SA_EAST = "sa-east-1"

    # Europe
    EU_WEST = "eu-west-1"         # Ireland
    EU_CENTRAL = "eu-central-1"   # Frankfurt (GDPR primary)
    EU_NORTH = "eu-north-1"       # Stockholm
    UK_SOUTH = "uk-south-1"       # London (post-Brexit)

    # Asia-Pacific
    AP_SOUTHEAST = "ap-southeast-1"
    AP_NORTHEAST = "ap-northeast-1"
    AP_SOUTH = "ap-south-1"

    # Sovereign / Air-Gapped
    LC1_EAST = "lc1-east"         # Liberty Center One (on-prem)
    LC1_WEST = "lc1-west"
    AIRGAP = "airgap-local"       # Fully disconnected


class ComplianceFramework(str, Enum):
    GDPR = "gdpr"                    # EU General Data Protection Regulation
    CCPA = "ccpa"                    # California Consumer Privacy Act
    HIPAA = "hipaa"                  # Health Insurance Portability (US)
    FEDRAMP = "fedramp"              # Federal Risk & Authorization (US Gov)
    SOC2 = "soc2"                    # Service Organization Control 2
    ISO27001 = "iso27001"            # Information Security Management
    PCI_DSS = "pci_dss"              # Payment Card Industry
    SOVEREIGN = "sovereign"          # National data sovereignty


# Region → Compliance framework mappings
REGION_COMPLIANCE: Dict[DataRegion, List[ComplianceFramework]] = {
    DataRegion.US_EAST: [ComplianceFramework.SOC2, ComplianceFramework.CCPA],
    DataRegion.US_WEST: [ComplianceFramework.SOC2, ComplianceFramework.CCPA],
    DataRegion.US_GOV: [ComplianceFramework.FEDRAMP, ComplianceFramework.SOC2, ComplianceFramework.HIPAA],
    DataRegion.CA_CENTRAL: [ComplianceFramework.SOC2],
    DataRegion.EU_CENTRAL: [ComplianceFramework.GDPR, ComplianceFramework.ISO27001, ComplianceFramework.SOC2],
    DataRegion.EU_WEST: [ComplianceFramework.GDPR, ComplianceFramework.ISO27001],
    DataRegion.EU_NORTH: [ComplianceFramework.GDPR, ComplianceFramework.ISO27001],
    DataRegion.UK_SOUTH: [ComplianceFramework.GDPR, ComplianceFramework.ISO27001],
    DataRegion.LC1_EAST: [ComplianceFramework.SOVEREIGN, ComplianceFramework.SOC2, ComplianceFramework.FEDRAMP],
    DataRegion.LC1_WEST: [ComplianceFramework.SOVEREIGN, ComplianceFramework.SOC2],
    DataRegion.AIRGAP: [ComplianceFramework.SOVEREIGN, ComplianceFramework.FEDRAMP,
                         ComplianceFramework.HIPAA, ComplianceFramework.SOC2],
}


# ============================================================================
#  DATA RESIDENCY POLICY
# ============================================================================

class ResidencyPolicy:
    """Per-tenant data residency policy."""

    def __init__(
        self,
        tenant_id: str,
        primary_region: DataRegion,
        allowed_regions: List[DataRegion] = None,
        required_frameworks: List[ComplianceFramework] = None,
        allow_cross_border: bool = False,
        encryption_required: bool = True,
        data_retention_days: int = 2555,  # 7 years default
        right_to_erasure: bool = True,    # GDPR Article 17
    ):
        self.tenant_id = tenant_id
        self.primary_region = primary_region
        self.allowed_regions = allowed_regions or [primary_region]
        self.required_frameworks = required_frameworks or []
        self.allow_cross_border = allow_cross_border
        self.encryption_required = encryption_required
        self.data_retention_days = data_retention_days
        self.right_to_erasure = right_to_erasure

    def is_region_allowed(self, region: DataRegion) -> bool:
        """Check if data can be stored/processed in a region."""
        if region in self.allowed_regions:
            return True
        if self.allow_cross_border:
            return True
        return False

    def get_compliance_status(self) -> Dict[str, Any]:
        """Check compliance status for the primary region."""
        region_frameworks = REGION_COMPLIANCE.get(self.primary_region, [])
        met = [f for f in self.required_frameworks if f in region_frameworks]
        unmet = [f for f in self.required_frameworks if f not in region_frameworks]

        return {
            "tenant_id": self.tenant_id,
            "primary_region": self.primary_region.value,
            "frameworks_required": [f.value for f in self.required_frameworks],
            "frameworks_met": [f.value for f in met],
            "frameworks_unmet": [f.value for f in unmet],
            "compliant": len(unmet) == 0,
            "encryption": self.encryption_required,
            "retention_days": self.data_retention_days,
            "right_to_erasure": self.right_to_erasure,
        }

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "primary_region": self.primary_region.value,
            "allowed_regions": [r.value for r in self.allowed_regions],
            "required_frameworks": [f.value for f in self.required_frameworks],
            "allow_cross_border": self.allow_cross_border,
            "encryption_required": self.encryption_required,
            "data_retention_days": self.data_retention_days,
            "right_to_erasure": self.right_to_erasure,
        }


# ============================================================================
#  RESIDENCY MANAGER
# ============================================================================

class ResidencyManager:
    """Manages data residency policies across tenants."""

    def __init__(self):
        self._policies: Dict[str, ResidencyPolicy] = {}

    def set_policy(self, policy: ResidencyPolicy):
        self._policies[policy.tenant_id] = policy
        logger.info(f"Data residency policy set for tenant {policy.tenant_id}: {policy.primary_region.value}")

    def get_policy(self, tenant_id: str) -> Optional[ResidencyPolicy]:
        return self._policies.get(tenant_id)

    def check_data_movement(self, tenant_id: str, target_region: DataRegion) -> Dict:
        """Check if data can be moved to a target region."""
        policy = self._policies.get(tenant_id)
        if not policy:
            return {"allowed": True, "reason": "no_policy_defined"}

        allowed = policy.is_region_allowed(target_region)
        return {
            "tenant_id": tenant_id,
            "source_region": policy.primary_region.value,
            "target_region": target_region.value,
            "allowed": allowed,
            "reason": "region_allowed" if allowed else "cross_border_blocked",
            "frameworks_at_target": [
                f.value for f in REGION_COMPLIANCE.get(target_region, [])
            ],
        }

    def get_gdpr_erasure_request(self, tenant_id: str, user_id: str) -> Dict:
        """Process a GDPR Article 17 Right to Erasure request."""
        policy = self._policies.get(tenant_id)
        if not policy or not policy.right_to_erasure:
            return {"status": "not_applicable"}

        return {
            "status": "pending",
            "tenant_id": tenant_id,
            "user_id": user_id,
            "data_types_to_erase": [
                "verification_jobs",
                "audit_logs_personal",
                "user_profile",
                "session_data",
            ],
            "data_types_retained": [
                "audit_chain_hashes",          # Integrity chain — anonymized
                "aggregated_usage_metrics",    # Non-personal
            ],
            "estimated_completion": "72 hours",
            "legal_basis": "GDPR Article 17(1)",
            "regions_affected": [r.value for r in (policy.allowed_regions if policy else [])],
        }

    def list_available_regions(self) -> List[Dict]:
        """List all available data regions with compliance info."""
        return [
            {
                "region": r.value,
                "frameworks": [f.value for f in REGION_COMPLIANCE.get(r, [])],
                "type": "sovereign" if "lc1" in r.value or "airgap" in r.value else "cloud",
            }
            for r in DataRegion
        ]

    def get_compliance_report(self, tenant_id: str) -> Dict:
        """Generate a compliance report for audit purposes."""
        policy = self._policies.get(tenant_id)
        if not policy:
            return {"status": "no_policy", "compliant": False}

        return {
            "tenant_id": tenant_id,
            "policy": policy.to_dict(),
            "compliance": policy.get_compliance_status(),
            "available_regions": len(DataRegion),
            "cross_border": policy.allow_cross_border,
        }


# Global singleton
residency_manager = ResidencyManager()
