def test_create_trip(client):
    boat = client.post("/api/v1/boats", json={
        "name": "B", "registration_number": "T-001", "capacity": 10.0
    }).json()
    crew = client.post("/api/v1/crews", json={
        "captain_name": "Cap", "members_count": 3
    }).json()
    response = client.post("/api/v1/trips", json={
        "boat_id": boat["id"],
        "crew_id": crew["id"],
        "departure_date": "2024-01-01T00:00:00",
        "return_date": "2024-01-10T00:00:00"
    })
    assert response.status_code == 201


def test_create_trip_invalid_boat(client):
    crew = client.post("/api/v1/crews", json={
        "captain_name": "Cap", "members_count": 3
    }).json()
    response = client.post("/api/v1/trips", json={
        "boat_id": 99999,
        "crew_id": crew["id"],
        "departure_date": "2024-01-01T00:00:00",
        "return_date": "2024-01-10T00:00:00"
    })
    assert response.status_code == 404


def test_create_trip_invalid_crew(client):
    boat = client.post("/api/v1/boats", json={
        "name": "B", "registration_number": "T-002", "capacity": 10.0
    }).json()
    response = client.post("/api/v1/trips", json={
        "boat_id": boat["id"],
        "crew_id": 99999,
        "departure_date": "2024-01-01T00:00:00",
        "return_date": "2024-01-10T00:00:00"
    })
    assert response.status_code == 404


def test_create_trip_return_before_departure(client):
    boat = client.post("/api/v1/boats", json={
        "name": "B", "registration_number": "T-003", "capacity": 10.0
    }).json()
    crew = client.post("/api/v1/crews", json={
        "captain_name": "Cap", "members_count": 3
    }).json()
    response = client.post("/api/v1/trips", json={
        "boat_id": boat["id"],
        "crew_id": crew["id"],
        "departure_date": "2024-01-10T00:00:00",
        "return_date": "2024-01-01T00:00:00"
    })
    assert response.status_code in (400, 422)
