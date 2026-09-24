import pytest
from pydantic import ValidationError
from backend.src.schemas import BoatCreate, CrewCreate, TripCreate


# BOAT
def test_boat_create_valid():
    boat = BoatCreate(name="Морской волк", registration_number="MR-001", capacity=10.0)
    assert boat.name == "Морской волк"
    assert boat.capacity == 10.0


def test_boat_create_negative_capacity():
    with pytest.raises(ValidationError):
        BoatCreate(name="Test", registration_number="MR-002", capacity=-5.0)


def test_boat_create_zero_capacity():
    with pytest.raises(ValidationError):
        BoatCreate(name="Test", registration_number="MR-003", capacity=0)


def test_boat_create_empty_name():
    with pytest.raises(ValidationError):
        BoatCreate(name="", registration_number="MR-004", capacity=10.0)


def test_boat_create_short_registration():
    with pytest.raises(ValidationError):
        BoatCreate(name="Test", registration_number="AB", capacity=10.0)


# CREW
def test_crew_create_valid():
    crew = CrewCreate(captain_name="Иван Иванов", members_count=5)
    assert crew.members_count == 5


def test_crew_create_zero_members():
    with pytest.raises(ValidationError):
        CrewCreate(captain_name="Test", members_count=0)


def test_crew_create_negative_members():
    with pytest.raises(ValidationError):
        CrewCreate(captain_name="Test", members_count=-1)
