"""
ТЕСТЫ
Интеграционные тесты для всех эндпоинтов.
Используют фикстуры из conftest.py — БД очищается перед каждым тестом.
"""


# ============================================
# ТЕСТЫ ДЛЯ BOAT
# ============================================


def test_create_boat(client):
    response = client.post(
        "/api/v1/boats",
        json={
            "name": "Морской волк",
            "registration_number": "MR-001",
            "capacity": 10.5,
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Морской волк"


def test_get_boats(client):
    response = client.get("/api/v1/boats")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_boat_not_found(client):
    response = client.get("/api/v1/boats/99999")
    assert response.status_code == 404


def test_update_boat(client):
    create = client.post(
        "/api/v1/boats",
        json={"name": "Старый", "registration_number": "UPD-001", "capacity": 5.0},
    ).json()
    response = client.put(f"/api/v1/boats/{create['id']}", json={"name": "Новый"})
    assert response.status_code == 200
    assert response.json()["name"] == "Новый"


def test_delete_boat(client):
    create = client.post(
        "/api/v1/boats",
        json={"name": "Удаляемый", "registration_number": "DEL-001", "capacity": 5.0},
    ).json()
    response = client.delete(f"/api/v1/boats/{create['id']}")
    assert response.status_code == 204


def test_duplicate_registration_number(client):
    client.post(
        "/api/v1/boats",
        json={"name": "Первый", "registration_number": "UNIQ-001", "capacity": 5.0},
    )
    response = client.post(
        "/api/v1/boats",
        json={"name": "Второй", "registration_number": "UNIQ-001", "capacity": 5.0},
    )
    assert response.status_code == 409


# ============================================
# ТЕСТЫ ДЛЯ CREW
# ============================================


def test_create_crew(client):
    response = client.post(
        "/api/v1/crews",
        json={"captain_name": "Иван Иванов", "members_count": 5},
    )
    assert response.status_code == 201


def test_get_crews(client):
    response = client.get("/api/v1/crews")
    assert response.status_code == 200


# ============================================
# ТЕСТЫ ДЛЯ TRIP
# ============================================


def test_create_trip(client):
    boat = client.post(
        "/api/v1/boats",
        json={"name": "Test Boat", "registration_number": "T-001", "capacity": 10.0},
    ).json()
    crew = client.post(
        "/api/v1/crews",
        json={"captain_name": "Test Captain", "members_count": 3},
    ).json()
    response = client.post(
        "/api/v1/trips",
        json={
            "boat_id": boat["id"],
            "crew_id": crew["id"],
            "departure_date": "2024-01-01T00:00:00",
            "return_date": "2024-01-10T00:00:00",
        },
    )
    assert response.status_code == 201


# ============================================
# HEALTH
# ============================================


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
