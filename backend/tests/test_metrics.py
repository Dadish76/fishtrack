from importlib import import_module

from prometheus_client import REGISTRY
from sqlalchemy.exc import OperationalError

from backend.src.metrics import APP_HEALTH

main_module = import_module("backend.src.main")


def test_metrics_endpoint(client):
    client.get("/version")
    client.get("/health")

    response = client.get("/metrics")

    assert response.status_code == 200

    body = response.text

    assert "fishtrack_http_requests_total" in body
    assert "fishtrack_http_errors_total" in body or ("fishtrack_http_errors" in body)
    assert "fishtrack_http_request_duration_seconds_bucket" in body
    assert "fishtrack_app_healthy" in body
    assert "fishtrack_trips_created_total" in body


def test_requests_counter(client):
    labels = {
        "method": "GET",
        "path": "/version",
        "status": "200",
    }

    before = (
        REGISTRY.get_sample_value(
            "fishtrack_http_requests_total",
            labels,
        )
        or 0
    )

    response = client.get("/version")

    after = REGISTRY.get_sample_value(
        "fishtrack_http_requests_total",
        labels,
    )

    assert response.status_code == 200
    assert after == before + 1


def test_errors_counter(client):
    labels = {
        "method": "GET",
        "path": "/api/v1/boats/{boat_id}",
        "status": "404",
    }

    before = (
        REGISTRY.get_sample_value(
            "fishtrack_http_errors_total",
            labels,
        )
        or 0
    )

    response = client.get("/api/v1/boats/999999")

    after = REGISTRY.get_sample_value(
        "fishtrack_http_errors_total",
        labels,
    )

    assert response.status_code == 404
    assert after == before + 1


def test_health_success(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "connected"

    assert APP_HEALTH._value.get() == 1


def test_health_database_failure(client, monkeypatch):
    class UnavailableEngine:
        def connect(self):
            raise OperationalError(
                "SELECT 1",
                {},
                Exception("Simulated DB outage"),
            )

    with monkeypatch.context() as patch:
        patch.setattr(
            main_module,
            "engine",
            UnavailableEngine(),
        )

        response = client.get("/health")

        assert response.status_code == 503
        assert response.json()["status"] == "unhealthy"
        assert response.json()["database"] == "unavailable"

        assert APP_HEALTH._value.get() == 0

    # После возврата нормального подключения
    # приложение снова должно быть готово.
    recovered = client.get("/health")

    assert recovered.status_code == 200
    assert APP_HEALTH._value.get() == 1


def test_liveness(client):
    response = client.get("/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_trips_created_metric(client):
    before = REGISTRY.get_sample_value("fishtrack_trips_created_total") or 0

    boat = client.post(
        "/api/v1/boats",
        json={
            "name": "Metric Test Boat",
            "registration_number": "METRIC-001",
            "capacity": 10.0,
        },
    )

    assert boat.status_code == 201

    crew = client.post(
        "/api/v1/crews",
        json={
            "captain_name": "Metric Captain",
            "members_count": 3,
        },
    )

    assert crew.status_code == 201

    trip = client.post(
        "/api/v1/trips",
        json={
            "boat_id": boat.json()["id"],
            "crew_id": crew.json()["id"],
            "departure_date": "2026-01-01T10:00:00",
            "return_date": "2026-01-02T10:00:00",
        },
    )

    assert trip.status_code == 201

    after = REGISTRY.get_sample_value("fishtrack_trips_created_total")

    assert after == before + 1
