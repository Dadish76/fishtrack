import json
import logging
import os
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """Безопасный формат журналов FishTrack."""

    def format(self, record):
        data = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=UTC,
            ).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", "application"),
            "method": getattr(record, "method", None),
            "path": getattr(record, "path", None),
            "status_code": getattr(record, "status_code", None),
            "result": getattr(record, "result", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "request_id": getattr(record, "request_id", None),
            "instance_id": os.getenv("INSTANCE_ID", "unknown"),
            "exception_type": getattr(record, "exception_type", None),
        }

        return json.dumps(
            data,
            ensure_ascii=False,
        )


def setup_logging():
    logger = logging.getLogger("fishtrack")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    logger.handlers.clear()
    logger.addHandler(handler)

    return logger
