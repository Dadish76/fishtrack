import json
import logging
from uuid import UUID

from backend.src.logging_config import JSONFormatter
from backend.src.main import logger


class CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.entries = []
        self.formatter = JSONFormatter()

    def emit(self, record):
        entry = json.loads(self.format(record))
        self.entries.append(entry)


def test_structured_logging(client):
    handler = CaptureHandler()
    logger.addHandler(handler)

    try:
        response = client.get("/version")
    finally:
        logger.removeHandler(handler)

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert "X-Instance-ID" in response.headers

    UUID(response.headers["X-Request-ID"])

    assert handler.entries

    entry = handler.entries[-1]

    assert entry["event"] == "http_request"
    assert entry["method"] == "GET"
    assert entry["path"] == "/version"
    assert entry["status_code"] == 200
    assert entry["result"] == "success"
    assert entry["level"] == "INFO"

    assert entry["timestamp"]
    assert entry["duration_ms"] >= 0

    assert entry["request_id"] == response.headers["X-Request-ID"]


def test_secrets_not_logged(client):
    secret = "FISHTRACK_TEST_SECRET_12345"

    handler = CaptureHandler()
    logger.addHandler(handler)

    try:
        response = client.post(
            "/login",
            params={"token": secret},
            data={
                "username": "nonexistent",
                "password": secret,
            },
            headers={
                "Authorization": f"Bearer {secret}",
            },
        )
    finally:
        logger.removeHandler(handler)

    assert response.status_code == 401
    assert handler.entries

    logs = json.dumps(handler.entries)

    assert secret not in logs


def test_error_logging(client):
    handler = CaptureHandler()
    logger.addHandler(handler)

    try:
        response = client.get("/api/v1/boats/999999")
    finally:
        logger.removeHandler(handler)

    assert response.status_code == 404

    entry = handler.entries[-1]

    assert entry["level"] == "WARNING"
    assert entry["status_code"] == 404
    assert entry["result"] == "client_error"
    assert entry["request_id"]
