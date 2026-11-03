from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .auth import create_session_token, get_current_user, login_user
from .database import get_db
from .models import Boat, Crew, Trip

router = APIRouter()
templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = login_user(username, password, db)
    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Неверный логин или пароль"},
            status_code=401,
        )
    token = create_session_token(user)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie("session", token, httponly=True, max_age=3600 * 24)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    return response


def current_user(request: Request, db: Session):
    """Хелпер для получения текущего пользователя в роутах."""
    return get_current_user(request, db)


# ============================================
# ГЛАВНАЯ
# ============================================


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request, name="index.html", context={"user": user}
    )


# ============================================
# BOAT
# ============================================


@router.get("/web/boats", response_class=HTMLResponse)
def web_boats(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    boats = db.query(Boat).all()
    return templates.TemplateResponse(
        request=request,
        name="boats.html",
        context={"boats": boats, "user": user},
    )


@router.get("/web/boats/new", response_class=HTMLResponse)
def web_boat_new(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="boat_form.html",
        context={"boat": None, "user": user},
    )


@router.post("/web/boats/new")
def web_boat_create(
    request: Request,
    name: str = Form(...),
    registration_number: str = Form(...),
    capacity: float = Form(...),
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Boat).filter(Boat.registration_number == registration_number).first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="Катер с таким номером уже существует"
        )
    boat = Boat(name=name, registration_number=registration_number, capacity=capacity)
    db.add(boat)
    db.commit()
    return RedirectResponse(url="/web/boats", status_code=303)


@router.get("/web/boats/{boat_id}/edit", response_class=HTMLResponse)
def web_boat_edit(boat_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    boat = db.query(Boat).filter(Boat.id == boat_id).first()
    if not boat:
        raise HTTPException(status_code=404, detail="Катер не найден")
    return templates.TemplateResponse(
        request=request,
        name="boat_form.html",
        context={"boat": boat, "user": user},
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


# ============================================
# CREW
# ============================================


@router.get("/web/crews", response_class=HTMLResponse)
def web_crews(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    crews = db.query(Crew).all()
    return templates.TemplateResponse(
        request=request,
        name="crews.html",
        context={"crews": crews, "user": user},
    )


@router.get("/web/crews/new", response_class=HTMLResponse)
def web_crew_new(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="crew_form.html",
        context={"crew": None, "user": user},
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
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if not crew:
        raise HTTPException(status_code=404, detail="Команда не найдена")
    return templates.TemplateResponse(
        request=request,
        name="crew_form.html",
        context={"crew": crew, "user": user},
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


# ============================================
# TRIP
# ============================================


@router.get("/web/trips", response_class=HTMLResponse)
def web_trips(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    trips = db.query(Trip).all()
    return templates.TemplateResponse(
        request=request,
        name="trips.html",
        context={"trips": trips, "user": user},
    )


@router.get("/web/trips/new", response_class=HTMLResponse)
def web_trip_new(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    boats = db.query(Boat).all()
    crews = db.query(Crew).all()
    return templates.TemplateResponse(
        request=request,
        name="trip_form.html",
        context={"trip": None, "boats": boats, "crews": crews, "user": user},
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
        raise HTTPException(
            status_code=400,
            detail="Дата возврата не может быть раньше даты отправления",
        )

    trip = Trip(
        boat_id=boat_id,
        crew_id=crew_id,
        departure_date=dep,
        return_date=ret,
    )
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
