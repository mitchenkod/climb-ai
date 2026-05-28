from dataclasses import dataclass
from typing import Sequence

import cv2
import numpy as np


@dataclass(frozen=True)
class ImagePoint:
    x: float
    y: float


def pixel_to_wall_normalized(
    x_px: float,
    y_px: float,
    work_area: Sequence[ImagePoint],
) -> tuple[float, float]:
    matrix = perspective_matrix(
        work_area,
        [
            ImagePoint(0.0, 0.0),
            ImagePoint(1.0, 0.0),
            ImagePoint(1.0, 1.0),
            ImagePoint(0.0, 1.0),
        ],
    )
    return transform_point(x_px, y_px, matrix)


def wall_normalized_to_pixel(
    x: float,
    y: float,
    work_area: Sequence[ImagePoint],
) -> tuple[float, float]:
    matrix = perspective_matrix(
        [
            ImagePoint(0.0, 0.0),
            ImagePoint(1.0, 0.0),
            ImagePoint(1.0, 1.0),
            ImagePoint(0.0, 1.0),
        ],
        work_area,
    )
    return transform_point(x, y, matrix)


def normalized_to_surface_coords(x: float, y: float, width_m: float, height_m: float) -> tuple[float, float]:
    return x * width_m, (1.0 - y) * height_m


def perspective_matrix(
    source: Sequence[ImagePoint],
    destination: Sequence[ImagePoint],
):
    if len(source) != 4 or len(destination) != 4:
        raise ValueError("Perspective transform requires exactly 4 source and destination points")

    source_points = np.float32([[point.x, point.y] for point in source])
    destination_points = np.float32([[point.x, point.y] for point in destination])
    return cv2.getPerspectiveTransform(source_points, destination_points)


def transform_point(x: float, y: float, matrix) -> tuple[float, float]:
    point = np.float32([[[x, y]]])
    transformed = cv2.perspectiveTransform(point, matrix)[0][0]
    return float(transformed[0]), float(transformed[1])
