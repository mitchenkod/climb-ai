from dataclasses import dataclass


@dataclass(frozen=True)
class SurfaceGeometry:
    width_m: float
    height_m: float
    image_width_px: float
    image_height_px: float
    angle_deg: float = 0.0

    @property
    def scale_x(self) -> float:
        return self.width_m / self.image_width_px

    @property
    def scale_y(self) -> float:
        return self.height_m / self.image_height_px


def normalized_to_pixel_coords(x: float, y: float, geometry: SurfaceGeometry) -> tuple[float, float]:
    return x * geometry.image_width_px, y * geometry.image_height_px


def pixel_to_surface_coords(
    x_px: float,
    y_px: float,
    geometry: SurfaceGeometry,
) -> tuple[float, float]:
    """Convert image pixels to meters in the local surface plane.

    Image coordinates have origin at the top-left corner. Surface coordinates
    have origin at the bottom-left corner and y grows upward.
    """
    x_m = x_px * geometry.scale_x
    y_m = geometry.height_m - (y_px * geometry.scale_y)
    return x_m, y_m
