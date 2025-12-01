import json
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

def logSystemEvent(event_type, message, level="INFO", metadata=None):
    log_entry = {
        "event_type": event_type,
        "message": message,
        "level": level,
        "metadata": metadata,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    logger.info(json.dumps(log_entry))