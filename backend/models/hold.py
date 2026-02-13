# backend/models/hold.py

from typing import Optional, List
from sqlmodel import Field, Relationship
from .base import BaseTable

class Hold(BaseTable, table=True):
    surface_id: Optional[int] = Field(default=None, foreign_key="surface.id")

    x: float
    y: float
    z: float

    hold_type: str
    size: Optional[str] = None

    surface: Optional["Surface"] = Relationship(back_populates="holds")
    routes: List["HoldInRoute"] = Relationship(back_populates="hold")
