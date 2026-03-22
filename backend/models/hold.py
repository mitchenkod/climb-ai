from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship
from .base import BaseTable

if TYPE_CHECKING:
    from .surface import Surface
    from .hold_in_route import HoldInRoute

class Hold(BaseTable, table=True):
    surface_id: Optional[int] = Field(default=None, foreign_key="surface.id")

    x: float
    y: float
    z: float

    hold_type: str
    size: Optional[str] = None

    surface: Mapped[Optional["Surface"]] = Relationship(back_populates="holds")
    routes: Mapped[List["HoldInRoute"]] = Relationship(back_populates="hold")
