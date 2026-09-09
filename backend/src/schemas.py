"""
PYDANTIC СХЕМЫ
DevB: Реализовать схемы для Boat, Crew, Trip

Для каждой сущности нужно:
1. Create схема (для POST запросов)
2. Response схема (для GET ответов, с id)

Подсказка: Используй BaseModel, Field, validator
"""

# from pydantic import BaseModel, Field, validator
# from datetime import datetime
# from typing import Optional

# TODO: Реализовать схему для Boat
# class BoatCreate(BaseModel):
#     ...

# class BoatResponse(BoatCreate):
#     id: int
#     class Config:
#         from_attributes = True

# TODO: Реализовать схему для Crew
# class CrewCreate(BaseModel):
#     ...

# class CrewResponse(CrewCreate):
#     id: int
#     class Config:
#         from_attributes = True

# TODO: Реализовать схему для Trip
# class TripCreate(BaseModel):
#     ...

# class TripResponse(TripCreate):
#     id: int
#     class Config:
#         from_attributes = True