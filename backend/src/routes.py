"""
API РОУТЕРЫ (CRUD)
DevB: Реализовать CRUD для Boat, Crew, Trip

Для каждой сущности нужно:
- GET /{entity} — список
- GET /{entity}/{id} — получить
- POST /{entity} — создать
- PUT /{entity}/{id} — обновить
- DELETE /{entity}/{id} — удалить

Бизнес-правило: registration_number должен быть уникальным
При создании Boat проверять, что номер не существует → 409 Conflict

Подсказка: Используй APIRouter, Depends(get_db), HTTPException
"""

# from fastapi import APIRouter, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# from typing import List
# from .database import get_db
# from .models import Boat, Crew, Trip
# from .schemas import BoatCreate, BoatResponse, CrewCreate, CrewResponse, TripCreate, TripResponse

# router = APIRouter()

# ============================================
# РОУТЕРЫ ДЛЯ BOAT
# ============================================

# TODO: GET /boats — список всех катеров
# @router.get("/boats", response_model=List[BoatResponse])
# def get_boats(db: Session = Depends(get_db)):
#     ...

# TODO: GET /boats/{id} — получить катер по id (404 если нет)
# @router.get("/boats/{boat_id}", response_model=BoatResponse)
# def get_boat(boat_id: int, db: Session = Depends(get_db)):
#     ...

# TODO: POST /boats — создать катер (проверить уникальность registration_number → 409)
# @router.post("/boats", response_model=BoatResponse, status_code=201)
# def create_boat(boat: BoatCreate, db: Session = Depends(get_db)):
#     ...

# TODO: PUT /boats/{id} — обновить катер (404 если нет)
# @router.put("/boats/{boat_id}", response_model=BoatResponse)
# def update_boat(boat_id: int, boat: BoatCreate, db: Session = Depends(get_db)):
#     ...

# TODO: DELETE /boats/{id} — удалить катер (404 если нет)
# @router.delete("/boats/{boat_id}", status_code=204)
# def delete_boat(boat_id: int, db: Session = Depends(get_db)):
#     ...

# ============================================
# РОУТЕРЫ ДЛЯ CREW (аналогично)
# ============================================

# TODO: GET /crews — список команд
# TODO: GET /crews/{id} — получить команду
# TODO: POST /crews — создать команду
# TODO: PUT /crews/{id} — обновить команду
# TODO: DELETE /crews/{id} — удалить команду

# ============================================
# РОУТЕРЫ ДЛЯ TRIP (аналогично)
# ============================================

# TODO: GET /trips — список рейсов
# TODO: GET /trips/{id} — получить рейс
# TODO: POST /trips — создать рейс
# TODO: PUT /trips/{id} — обновить рейс
# TODO: DELETE /trips/{id} — удалить рейс