from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship
from .base import BaseTable
from backend.geometry.normalization import (
    SurfaceGeometry,
    normalized_to_pixel_coords,
    pixel_to_surface_coords,
)

if TYPE_CHECKING:
    from .wall import Wall
    from .hold import Hold

class Surface(BaseTable, table=True):
    wall_id: Optional[int] = Field(default=None, foreign_key="wall.id")

    angle: float        # угол наклона
    width: float
    height: float
    width_m: float = 1.0
    height_m: float = 1.0
    image_width_px: int = 1
    image_height_px: int = 1

    origin_x: float     # положение в глобальной системе
    origin_y: float
    origin_z: float

    normal_x: float     # нормаль поверхности
    normal_y: float
    normal_z: float

    wall: Mapped[Optional["Wall"]] = Relationship(back_populates="surfaces")
    holds: Mapped[List["Hold"]] = Relationship(back_populates="surface")

    def geometry(self) -> SurfaceGeometry:
        return SurfaceGeometry(
            width_m=self.width_m,
            height_m=self.height_m,
            image_width_px=self.image_width_px,
            image_height_px=self.image_height_px,
            angle_deg=self.angle,
        )

    def normalized_to_pixel_coords(self, x: float, y: float) -> tuple[float, float]:
        return normalized_to_pixel_coords(x, y, self.geometry())

    def pixel_to_surface_coords(self, x_px: float, y_px: float) -> tuple[float, float]:
        return pixel_to_surface_coords(x_px, y_px, self.geometry())
