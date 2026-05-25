from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship
from .base import BaseTable

if TYPE_CHECKING:
    from .surface import Surface
    from .hold_in_route import HoldInRoute

class Hold(BaseTable, table=True):
    surface_id: Optional[int] = Field(default=None, foreign_key="surface.id")

    # Legacy normalized image coordinates, kept for UI compatibility.
    x: float
    y: float
    z: float
    x_px: Optional[float] = None
    y_px: Optional[float] = None
    x_m: Optional[float] = None
    y_m: Optional[float] = None

    hold_type: str
    size: Optional[str] = None
    quality: int = Field(default=5, ge=1, le=10)
    force_vectors: str = "[]"

    surface: Mapped[Optional["Surface"]] = Relationship(back_populates="holds")
    routes: Mapped[List["HoldInRoute"]] = Relationship(back_populates="hold")

    def world_coords(self) -> tuple[float, float, float]:
        return (
            self.x_m if self.x_m is not None else self.x,
            self.y_m if self.y_m is not None else self.y,
            self.z,
        )
