"""
МОДЕЛИ SQLALCHEMY
DevB: Реализовать 3 модели: Boat, Crew, Trip

Boat (Катер):
- id: int (primary key)
- name: str (название)
- registration_number: str (уникальный)
- capacity: float (вместимость)

Crew (Команда):
- id: int (primary key)
- captain_name: str (капитан)
- members_count: int (количество членов)

Trip (Рейс):
- id: int (primary key)
- boat_id: int (foreign key → Boat)
- crew_id: int (foreign key → Crew)
- departure_date: datetime
- return_date: datetime (может быть null)

Связи:
- Boat → Trips (1:N)
- Crew → Trips (1:N)

Подсказка: Используй Column, Integer, String, Float, DateTime, ForeignKey
"""

# from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
# from sqlalchemy.orm import relationship
# from .database import Base

# TODO: Реализовать класс Boat
# class Boat(Base):
#     __tablename__ = "boats"
#     ...

# TODO: Реализовать класс Crew
# class Crew(Base):
#     __tablename__ = "crews"
#     ...

# TODO: Реализовать класс Trip
# class Trip(Base):
#     __tablename__ = "trips"
#     ...