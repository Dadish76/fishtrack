def test_create_trip(client):
    boat = client.post(
        "/api/v1/boats",
        json={"name": "B", "registration_number": "T-001", "capacity": 10.0},
    ).json()
    crew = client.post(
        "/api/v1/crews", json={"captain_name": "Cap", "members_count": 3}
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


def test_create_trip_invalid_boat(client):
    crew = client.post(
        "/api/v1/crews", json={"captain_name": "Cap", "members_count": 3}
    ).json()
    response = client.post(
        "/api/v1/trips",
        json={
            "boat_id": 99999,
            "crew_id": crew["id"],
            "departure_date": "2024-01-01T00:00:00",
            "return_date": "2024-01-10T00:00:00",
        },
    )
    assert response.status_code == 404


def test_create_trip_invalid_crew(client):
    boat = client.post(
        "/api/v1/boats",
        json={"name": "B", "registration_number": "T-002", "capacity": 10.0},
    ).json()
    response = client.post(
        "/api/v1/trips",
        json={
            "boat_id": boat["id"],
            "crew_id": 99999,
            "departure_date": "2024-01-01T00:00:00",
            "return_date": "2024-01-10T00:00:00",
        },
    )
    assert response.status_code == 404


def test_create_trip_return_before_departure(client):
    boat = client.post(
        "/api/v1/boats",
        json={"name": "B", "registration_number": "T-003", "capacity": 10.0},
    ).json()
    crew = client.post(
        "/api/v1/crews", json={"captain_name": "Cap", "members_count": 3}
    ).json()
    response = client.post(
        "/api/v1/trips",
        json={
            "boat_id": boat["id"],
            "crew_id": crew["id"],
            "departure_date": "2024-01-10T00:00:00",
            "return_date": "2024-01-01T00:00:00",
        },
    )
    assert response.status_code in (400, 422)


def create_trips_for_return_date_filter(client):
    """Создает два рейса с различным наличием даты возвращения."""

    boat_response = client.post(
        "/api/v1/boats",
        json={
            "name": "Filter Test Boat",
            "registration_number": "FILTER-001",
            "capacity": 10.0,
        },
    )
    assert boat_response.status_code == 201
    boat = boat_response.json()

    crew_response = client.post(
        "/api/v1/crews",
        json={
            "captain_name": "Filter Test Captain",
            "members_count": 3,
        },
    )
    assert crew_response.status_code == 201
    crew = crew_response.json()

    # Рейс с указанной датой возвращения.
    with_return = client.post(
        "/api/v1/trips",
        json={
            "boat_id": boat["id"],
            "crew_id": crew["id"],
            "departure_date": "2026-11-25T08:00:00",
            "return_date": "2026-11-25T18:00:00",
        },
    )
    assert with_return.status_code == 201

    # Рейс без указанной даты возвращения.
    without_return = client.post(
        "/api/v1/trips",
        json={
            "boat_id": boat["id"],
            "crew_id": crew["id"],
            "departure_date": "2026-11-26T08:00:00",
        },
    )
    assert without_return.status_code == 201

    return with_return.json()["id"], without_return.json()["id"]


def test_get_trips_without_return_date_filter(client):
    with_return, without_return = create_trips_for_return_date_filter(client)

    response = client.get("/api/v1/trips")

    assert response.status_code == 200

    ids = {trip["id"] for trip in response.json()}

    assert ids == {with_return, without_return}


def test_get_trips_with_return_date(client):
    with_return, _ = create_trips_for_return_date_filter(client)

    response = client.get(
        "/api/v1/trips",
        params={"has_return_date": "true"},
    )

    assert response.status_code == 200

    trips = response.json()

    assert len(trips) == 1
    assert trips[0]["id"] == with_return
    assert trips[0]["return_date"] is not None


def test_get_trips_without_return_date(client):
    _, without_return = create_trips_for_return_date_filter(client)

    response = client.get(
        "/api/v1/trips",
        params={"has_return_date": "false"},
    )

    assert response.status_code == 200

    trips = response.json()

    assert len(trips) == 1
    assert trips[0]["id"] == without_return
    assert trips[0]["return_date"] is None


def test_get_trips_invalid_return_date_filter(client):
    response = client.get(
        "/api/v1/trips",
        params={"has_return_date": "invalid"},
    )

    assert response.status_code == 400


def test_get_trips_return_date_filter_empty_result(client):
    response = client.get(
        "/api/v1/trips",
        params={"has_return_date": "true"},
    )

    assert response.status_code == 200
    assert response.json() == []
