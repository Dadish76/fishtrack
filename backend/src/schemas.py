from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional

# Boat
class BoatBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    registration_number: str = Field(..., min_length=3, max_length=20)
    capacity: float = Field(..., gt=0)
    year_built: Optional[int] = Field(None, ge=1900, le=2100)

    @validator('capacity')
    def capacity_positive(cls, v):
        if v <= 0:
            raise ValueError('Вместимость должна быть больше 0')
        return v

class BoatCreate(BoatBase):
    pass

class BoatUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    registration_number: Optional[str] = Field(None, min_length=3, max_length=20)
    capacity: Optional[float] = Field(None, gt=0)
    year_built: Optional[int] = Field(None, ge=1900, le=2100)

class BoatResponse(BoatBase):
    id: int

    class Config:
        from_attributes = True


# Crew
class CrewBase(BaseModel):
    captain_name: str = Field(..., min_length=1, max_length=100)
    members_count: int = Field(..., gt=0)

class CrewCreate(CrewBase):
    pass

class CrewUpdate(BaseModel):
    captain_name: Optional[str] = Field(None, min_length=1, max_length=100)
    members_count: Optional[int] = Field(None, gt=0)

class CrewResponse(CrewBase):
    id: int

    class Config:
        from_attributes = True


# Trip
class TripBase(BaseModel):
    boat_id: int
    crew_id: int
    departure_date: datetime
    return_date: Optional[datetime] = None

class TripCreate(TripBase):
    pass

class TripUpdate(BaseModel):
    boat_id: Optional[int] = None
    crew_id: Optional[int] = None
    departure_date: Optional[datetime] = None
    return_date: Optional[datetime] = None

class TripResponse(TripBase):
    id: int

    class Config:
        from_attributes = True
