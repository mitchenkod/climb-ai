from typing import Optional, List, TYPE_CHECKING
import json
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship
from .base import BaseTable
from backend.geometry.normalization import (
    SurfaceGeometry,
    normalized_to_pixel_coords,
    pixel_to_surface_coords,
)
from backend.geometry.projection import (
    ImagePoint,
    normalized_to_surface_coords,
    pixel_to_wall_normalized,
    wall_normalized_to_pixel,
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
    work_area: str = "[]"

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
        points = self.work_area_points()
        if points:
            return wall_normalized_to_pixel(x, y, points)
        return normalized_to_pixel_coords(x, y, self.geometry())

    def pixel_to_surface_coords(self, x_px: float, y_px: float) -> tuple[float, float]:
        points = self.work_area_points()
        if points:
            x, y = pixel_to_wall_normalized(x_px, y_px, points)
            return normalized_to_surface_coords(x, y, self.width_m, self.height_m)
        return pixel_to_surface_coords(x_px, y_px, self.geometry())

    def pixel_to_normalized_coords(self, x_px: float, y_px: float) -> tuple[float, float]:
        points = self.work_area_points()
        if points:
            return pixel_to_wall_normalized(x_px, y_px, points)
        return (
            x_px / self.image_width_px if self.image_width_px else 0.0,
            y_px / self.image_height_px if self.image_height_px else 0.0,
        )

    def work_area_points(self) -> List[ImagePoint]:
        try:
            raw_points = json.loads(self.work_area or "[]")
        except ValueError:
            return []
        if len(raw_points) != 4:
            return []
        return [ImagePoint(x=float(point["x"]), y=float(point["y"])) for point in raw_points]
