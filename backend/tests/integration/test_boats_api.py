def test_create_boat(client):
    response = client.post("/api/v1/boats", json={
        "name": "Морской волк",
        "registration_number": "MR-001",
        "capacity": 10.5
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Морской волк"
    assert data["registration_number"] == "MR-001"


def test_get_boats(client):
    # Создаём катер и проверяем ответ
    create_response = client.post("/api/v1/boats", json={
        "name": "Boat 1",
        "registration_number": "B-001",
        "capacity": 5.0
    })
    print(f"POST status: {create_response.status_code}")
    print(f"POST body: {create_response.json()}")
    assert create_response.status_code == 201   # ← проверка

    # Получаем список
    response = client.get("/api/v1/boats")
    print(f"GET status: {response.status_code}")
    print(f"GET body: {response.json()}")
    assert response.status_code == 200
    assert len(response.json()) == 1

def test_get_boat_not_found(client):
    response = client.get("/api/v1/boats/99999")
    assert response.status_code == 404


def test_duplicate_registration_number(client):
    client.post("/api/v1/boats", json={
        "name": "First", "registration_number": "DUP-001", "capacity": 5.0
    })
    response = client.post("/api/v1/boats", json={
        "name": "Second", "registration_number": "DUP-001", "capacity": 5.0
    })
    assert response.status_code == 409


def test_update_boat(client):
    boat = client.post("/api/v1/boats", json={
        "name": "Old", "registration_number": "UPD-001", "capacity": 5.0
    }).json()
    response = client.put(f"/api/v1/boats/{boat['id']}", json={
        "name": "New", "registration_number": "UPD-001", "capacity": 10.0
    })
    assert response.status_code == 200
    assert response.json()["name"] == "New"


def test_delete_boat(client):
    boat = client.post("/api/v1/boats", json={
        "name": "Del", "registration_number": "DEL-001", "capacity": 5.0
    }).json()
    response = client.delete(f"/api/v1/boats/{boat['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/v1/boats/{boat['id']}").status_code == 404

def test_create_boat_with_year_built(client):
    """Создание катера с годом постройки."""
    response = client.post("/api/v1/boats", json={
        "name": "Old Boat",
        "registration_number": "OLD-001",
        "capacity": 10.0,
        "year_built": 1995
    })
    assert response.status_code == 201
    assert response.json()["year_built"] == 1995


def test_create_boat_invalid_year(client):
    """Год постройки меньше 1900 — ошибка 422."""
    response = client.post("/api/v1/boats", json={
        "name": "Future Boat",
        "registration_number": "FUT-001",
        "capacity": 10.0,
        "year_built": 1800   # меньше 1900
    })
    assert response.status_code in (400, 422)


def test_create_boat_without_year_built(client):
    """Поле year_built опционально — можно не указывать."""
    response = client.post("/api/v1/boats", json={
        "name": "New Boat",
        "registration_number": "NEW-001",
        "capacity": 10.0
    })
    assert response.status_code == 201
    assert response.json()["year_built"] is None


def test_create_boat_year_in_future(client):
    """Год постройки больше 2100 — ошибка 422."""
    response = client.post("/api/v1/boats", json={
        "name": "Too Future",
        "registration_number": "TOO-001",
        "capacity": 10.0,
        "year_built": 2200
    })
    assert response.status_code in (400, 422)
