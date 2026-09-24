from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import Boat, Crew, Trip
from .schemas import (
    BoatCreate,
    BoatResponse,
    BoatUpdate,
    CrewCreate,
    CrewResponse,
    CrewUpdate,
    TripCreate,
    TripResponse,
    TripUpdate,
)

router = APIRouter()


# BOAT
@router.get("/boats", response_model=list[BoatResponse])
def get_boats(db: Session = Depends(get_db)):
    return db.query(Boat).all()


@router.get("/boats/{boat_id}", response_model=BoatResponse)
def get_boat(boat_id: int, db: Session = Depends(get_db)):
    boat = db.query(Boat).filter(Boat.id == boat_id).first()
    if not boat:
        raise HTTPException(status_code=404, detail="Катер не найден")
    return boat


@router.post("/boats", response_model=BoatResponse, status_code=status.HTTP_201_CREATED)
def create_boat(boat: BoatCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(Boat)
        .filter(Boat.registration_number == boat.registration_number)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Катер с таким номером уже существует"
        )
    db_boat = Boat(**boat.model_dump())
    db.add(db_boat)
    db.commit()
    db.refresh(db_boat)
    return db_boat


@router.put("/boats/{boat_id}", response_model=BoatResponse)
def update_boat(boat_id: int, boat: BoatUpdate, db: Session = Depends(get_db)):
    db_boat = db.query(Boat).filter(Boat.id == boat_id).first()
    if not db_boat:
        raise HTTPException(status_code=404, detail="Катер не найден")
    for key, value in boat.model_dump(exclude_unset=True).items():
        setattr(db_boat, key, value)
    db.commit()
    db.refresh(db_boat)
    return db_boat


@router.delete("/boats/{boat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_boat(boat_id: int, db: Session = Depends(get_db)):
    boat = db.query(Boat).filter(Boat.id == boat_id).first()
    if not boat:
        raise HTTPException(status_code=404, detail="Катер не найден")
    db.delete(boat)
    db.commit()


# CREW
@router.get("/crews", response_model=list[CrewResponse])
def get_crews(db: Session = Depends(get_db)):
    return db.query(Crew).all()


@router.get("/crews/{crew_id}", response_model=CrewResponse)
def get_crew(crew_id: int, db: Session = Depends(get_db)):
    crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Команда не найдена")
    return crew


@router.post("/crews", response_model=CrewResponse, status_code=status.HTTP_201_CREATED)
def create_crew(crew: CrewCreate, db: Session = Depends(get_db)):
    db_crew = Crew(**crew.model_dump())
    db.add(db_crew)
    db.commit()
    db.refresh(db_crew)
    return db_crew


@router.put("/crews/{crew_id}", response_model=CrewResponse)
def update_crew(crew_id: int, crew: CrewUpdate, db: Session = Depends(get_db)):
    db_crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if not db_crew:
        raise HTTPException(status_code=404, detail="Команда не найдена")
    for key, value in crew.dict(exclude_unset=True).items():
        setattr(db_crew, key, value)
    db.commit()
    db.refresh(db_crew)
    return db_crew


@router.delete("/crews/{crew_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crew(crew_id: int, db: Session = Depends(get_db)):
    crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Команда не найдена")
    db.delete(crew)
    db.commit()


# TRIP
@router.get("/trips", response_model=list[TripResponse])
def get_trips(db: Session = Depends(get_db)):
    return db.query(Trip).all()


@router.get("/trips/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Рейс не найден")
    return trip


@router.post("/trips", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
def create_trip(trip: TripCreate, db: Session = Depends(get_db)):
    # Проверяем катер
    boat = db.query(Boat).filter(Boat.id == trip.boat_id).first()
    if not boat:
        raise HTTPException(status_code=404, detail="Катер не найден")

    # Проверяем команду
    crew = db.query(Crew).filter(Crew.id == trip.crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Команда не найдена")

    if trip.return_date and trip.return_date < trip.departure_date:
        raise HTTPException(
            status_code=400,
            detail="Дата возврата не может быть раньше даты отправления",
        )

    db_trip = Trip(**trip.model_dump())
    db.add(db_trip)
    db.commit()
    db.refresh(db_trip)
    return db_trip


@router.put("/trips/{trip_id}", response_model=TripResponse)
def update_trip(trip_id: int, trip: TripUpdate, db: Session = Depends(get_db)):
    db_trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not db_trip:
        raise HTTPException(status_code=404, detail="Рейс не найден")
    for key, value in trip.dict(exclude_unset=True).items():
        setattr(db_trip, key, value)
    db.commit()
    db.refresh(db_trip)
    return db_trip


@router.delete("/trips/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Рейс не найден")
    db.delete(trip)
    db.commit()
