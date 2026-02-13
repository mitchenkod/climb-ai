from typing import Optional, List
from sqlmodel import Field, Relationship
from .base import BaseTable

class Surface(BaseTable, table=True):
    wall_id: Optional[int] = Field(default=None, foreign_key="wall.id")

    angle: float        # угол наклона
    width: float
    height: float

    origin_x: float     # положение в глобальной системе
    origin_y: float
    origin_z: float

    normal_x: float     # нормаль поверхности
    normal_y: float
    normal_z: float

    wall: Optional["Wall"] = Relationship(back_populates="surfaces")
    holds: List["Hold"] = Relationship(back_populates="surface")
