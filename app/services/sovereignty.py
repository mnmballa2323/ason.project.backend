from data_sovereignty import data_sovereignty, Jurisdiction, DataCategory, TransferMechanism

# Expose the singleton controller
# The actual logic remains in data_sovereignty.py (which is a shared lib or root module)
# This service file acts as the clean interface for the new app structure.

__all__ = ["data_sovereignty", "Jurisdiction", "DataCategory", "TransferMechanism"]
