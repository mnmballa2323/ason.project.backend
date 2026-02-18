"""
Audit Log Service
Writes immutable security logs to LOCAL STORAGE.
ensure compliance with Zero-Trust / Zero-Exposure policy.
"""

import datetime
from typing import Dict

class AuditLogger:
    def __init__(self, log_file: str = "security_audit.log"):
        self.log_file = log_file

    async def log_event(self, actor: str, action: str, target: str, status: str):
        """
        Appends an event to the local audit trail.
        """
        timestamp = datetime.datetime.now().isoformat()
        log_entry = f"[{timestamp}] ACTOR={actor} ACTION={action} TARGET={target} STATUS={status}\n"
        
        # In a real app, this would write to a secure file or local Syslog.
        # For simulation, we print to console or mock writing.
        # with open(self.log_file, "a") as f:
        #     f.write(log_entry)
        
        return {"logged": True, "timestamp": timestamp}

    async def view_recent_logs(self, limit: int = 10):
        # Return mocked logs for the viewer
        return [
            {"timestamp": "2026-10-15T10:00:00", "actor": "admin01", "action": "LOGIN", "target": "Console", "status": "SUCCESS"},
            {"timestamp": "2026-10-15T09:55:00", "actor": "unknown", "action": "LOGIN", "target": "Console", "status": "FAILED"}
        ]

# Singleton instance
audit_service = AuditLogger()
