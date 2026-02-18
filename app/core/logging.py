import logging
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    """Government-grade structured JSON log formatter."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "deployment": "Liberty Center One",
        }
        if hasattr(record, "job_id"):
            log_entry["job_id"] = record.job_id
        if hasattr(record, "actor"):
            log_entry["actor"] = record.actor
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

def setup_logging():
    log_handler = logging.StreamHandler()
    log_handler.setFormatter(JSONFormatter())

    logger = logging.getLogger("qwen.orchestrator")
    logger.setLevel(logging.INFO)
    logger.addHandler(log_handler)
    logger.propagate = False
    return logger

logger = setup_logging()
