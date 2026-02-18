"""
Service Catalog Service
Registry of available internal services for employees.
STRICTLY INTERNAL USE ONLY.
"""

from typing import List, Dict, Any

class ServiceCatalog:
    def __init__(self):
        self.catalog = [
            {
                "id": "hr-001",
                "category": "HR",
                "name": "Access Paystub",
                "agent": "payroll-administrator",
                "action": "process_payroll", # Mapping to agent action
                "description": "View your latest paystub and tax withholdings."
            },
            {
                "id": "it-001",
                "category": "IT",
                "name": "Password Reset",
                "agent": "it-administrator",
                "action": "provision_user",
                "description": "Reset your domain password."
            },
            {
                "id": "edu-001",
                "category": "Training",
                "name": "Enroll in Course",
                "agent": "curriculum-developer",
                "action": "create_module", 
                "description": "Sign up for internal compliance training."
            },
            {
                "id": "legal-001",
                "category": "Legal",
                "name": "Review Contract",
                "agent": "contract-analyst",
                "action": "review_clause",
                "description": "Submit a document for automated legal review."
            }
        ]

    async def get_catalog(self) -> List[Dict[str, Any]]:
        return self.catalog

    async def get_service(self, service_id: str) -> Dict[str, Any]:
        for service in self.catalog:
            if service["id"] == service_id:
                return service
        return None

# Singleton
catalog_service = ServiceCatalog()
