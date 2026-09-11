from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from .database import get_db
from .models import Boat, Crew, Trip

router = APIRouter()
templates = Jinja2Templates(directory="backend/src/templates")


# ГЛАВНАЯ
@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# BOAT
@router.get("/web/boats", response_class=HTMLResponse)
def web_boats(request: Request, db: Session = Depends(get_db)):
    boats = db.query(Boat).all()
    return templates.TemplateResponse(
        request=request,
        name="boats.html",
        context={"boats": boats}
    )


@router.get("/web/boats/new", response_class=HTMLResponse)
def web_boat_new(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="boat_form.html",
        context={"boat": None}
    )


@router.post("/web/boats/new")
def web_boat_create(
    name: str = Form(...),
    registration_number: str = Form(...),
    capacity: float = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(Boat).filter(Boat.registration_number == registration_number).first()
    if existing:
        raise HTTPException(status_code=409, detail="Катер с таким номером уже существует")

    boat = Boat(name=name, registration_number=registration_number, capacity=capacity)
    db.add(boat)
    db.commit()
    return RedirectResponse(url="/web/boats", status_code=303)


@router.get("/web/boats/{boat_id}/edit", response_class=HTMLResponse)
def web_boat_edit(boat_id: int, request: Request, db: Session = Depends(get_db)):
    boat = db.query(Boat).filter(Boat.id == boat_id).first()
    if not boat:
        raise HTTPException(status_code=404, detail="Катер не найден")
    return templates.TemplateResponse(
        request=request,
        name="boat_form.html",
        context={"boat": boat}
    )


@router.post("/web/boats/{boat_id}/edit")
def web_boat_update(
    boat_id: int,
    name: str = Form(...),
    registration_number: str = Form(...),
    capacity: float = Form(...),
    db: Session = Depends(get_db),
):
    boat = db.query(Boat).filter(Boat.id == boat_id).first()
    if not boat:
        raise HTTPException(status_code=404, detail="Катер не найден")
    boat.name = name
    boat.registration_number = registration_number
    boat.capacity = capacity
    db.commit()
    return RedirectResponse(url="/web/boats", status_code=303)


@router.post("/web/boats/{boat_id}/delete")
def web_boat_delete(boat_id: int, db: Session = Depends(get_db)):
    boat = db.query(Boat).filter(Boat.id == boat_id).first()
    if not boat:
        raise HTTPException(status_code=404, detail="Катер не найден")
    db.delete(boat)
    db.commit()
    return RedirectResponse(url="/web/boats", status_code=303)


# CREW
@router.get("/web/crews", response_class=HTMLResponse)
def web_crews(request: Request, db: Session = Depends(get_db)):
    crews = db.query(Crew).all()
    return templates.TemplateResponse(
        request=request,
        name="crews.html",
        context={"crews": crews}
    )


@router.get("/web/crews/new", response_class=HTMLResponse)
def web_crew_new(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="crew_form.html",
        context={"crew": None}
    )


@router.post("/web/crews/new")
def web_crew_create(
    captain_name: str = Form(...),
    members_count: int = Form(...),
    db: Session = Depends(get_db),
):
    crew = Crew(captain_name=captain_name, members_count=members_count)
    db.add(crew)
    db.commit()
    return RedirectResponse(url="/web/crews", status_code=303)


@router.get("/web/crews/{crew_id}/edit", response_class=HTMLResponse)
def web_crew_edit(crew_id: int, request: Request, db: Session = Depends(get_db)):
    crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Команда не найдена")
    return templates.TemplateResponse(
        request=request,
        name="crew_form.html",
        context={"crew": crew}
    )


@router.post("/web/crews/{crew_id}/edit")
def web_crew_update(
    crew_id: int,
    captain_name: str = Form(...),
    members_count: int = Form(...),
    db: Session = Depends(get_db),
):
    crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Команда не найдена")
    crew.captain_name = captain_name
    crew.members_count = members_count
    db.commit()
    return RedirectResponse(url="/web/crews", status_code=303)


@router.post("/web/crews/{crew_id}/delete")
def web_crew_delete(crew_id: int, db: Session = Depends(get_db)):
    crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Команда не найдена")
    db.delete(crew)
    db.commit()
    return RedirectResponse(url="/web/crews", status_code=303)


# TRIP
@router.get("/web/trips", response_class=HTMLResponse)
def web_trips(request: Request, db: Session = Depends(get_db)):
    trips = db.query(Trip).all()
    return templates.TemplateResponse(
        request=request,
        name="trips.html",
        context={"trips": trips}
    )


@router.get("/web/trips/new", response_class=HTMLResponse)
def web_trip_new(request: Request, db: Session = Depends(get_db)):
    boats = db.query(Boat).all()
    crews = db.query(Crew).all()
    return templates.TemplateResponse(
        request=request,
        name="trip_form.html",
        context={"trip": None, "boats": boats, "crews": crews}
    )


@router.post("/web/trips/new")
def web_trip_create(
    boat_id: int = Form(...),
    crew_id: int = Form(...),
    departure_date: str = Form(...),
    return_date: str = Form(...),
    db: Session = Depends(get_db),
):
    boat = db.query(Boat).filter(Boat.id == boat_id).first()
    if not boat:
        raise HTTPException(status_code=404, detail="Катер не найден")
    crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Команда не найдена")

    dep = datetime.fromisoformat(departure_date)
    ret = datetime.fromisoformat(return_date)
    if ret < dep:
        raise HTTPException(status_code=400, detail="Дата возврата не может быть раньше даты отправления")

    trip = Trip(boat_id=boat_id, crew_id=crew_id, departure_date=dep, return_date=ret)
    db.add(trip)
    db.commit()
    return RedirectResponse(url="/web/trips", status_code=303)


@router.post("/web/trips/{trip_id}/delete")
def web_trip_delete(trip_id: int, db: Session = Depends(get_db)):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Рейс не найден")
    db.delete(trip)
    db.commit()
    return RedirectResponse(url="/web/trips", status_code=303)