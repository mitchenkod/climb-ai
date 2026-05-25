from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from backend.db import get_session
from backend.models.wall import Wall
from backend.models.surface import Surface
from backend.models.hold import Hold
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class WallInput(BaseModel):
    gym_id: int
    image_name: str = "wall.jpg"
    width: Optional[float] = None
    height: Optional[float] = None
    width_m: Optional[float] = None
    height_m: Optional[float] = None
    image_width_px: int = 1
    image_height_px: int = 1
    angle: float = 0.0

class HoldInput(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None
    x_px: Optional[float] = None
    y_px: Optional[float] = None
    hold_type: str
    size: Optional[str] = None

class HoldsInput(BaseModel):
    holds: List[HoldInput]


class SurfaceGeometryInput(BaseModel):
    width_m: float
    height_m: float
    image_width_px: int
    image_height_px: int
    angle: Optional[float] = None


def surface_dimensions(data: WallInput) -> tuple[float, float]:
    width_m = data.width_m if data.width_m is not None else data.width
    height_m = data.height_m if data.height_m is not None else data.height
    return width_m or 1.0, height_m or 1.0


def build_default_surface(wall_id: int, data: Optional[WallInput] = None) -> Surface:
    width_m, height_m = surface_dimensions(data) if data else (1.0, 1.0)
    image_width_px = data.image_width_px if data else 1
    image_height_px = data.image_height_px if data else 1
    angle = data.angle if data else 0.0

    return Surface(
        wall_id=wall_id,
        angle=angle,
        width=width_m,
        height=height_m,
        width_m=width_m,
        height_m=height_m,
        image_width_px=image_width_px,
        image_height_px=image_height_px,
        origin_x=0,
        origin_y=0,
        origin_z=0,
        normal_x=0,
        normal_y=0,
        normal_z=1,
    )


def hold_coordinates(hold_data: HoldInput, surface: Surface) -> tuple[float, float, float, float, float, float]:
    if hold_data.x_px is not None and hold_data.y_px is not None:
        x_px = hold_data.x_px
        y_px = hold_data.y_px
        x = x_px / surface.image_width_px if surface.image_width_px else 0
        y = y_px / surface.image_height_px if surface.image_height_px else 0
    elif hold_data.x is not None and hold_data.y is not None:
        x = hold_data.x
        y = hold_data.y
        x_px, y_px = surface.normalized_to_pixel_coords(x, y)
    else:
        raise HTTPException(status_code=422, detail="Hold requires x/y or x_px/y_px")

    x_m, y_m = surface.pixel_to_surface_coords(x_px, y_px)
    return x, y, x_px, y_px, x_m, y_m


def recalculate_surface_holds(surface: Surface):
    for hold in surface.holds:
        if hold.x_px is not None and hold.y_px is not None:
            x_px = hold.x_px
            y_px = hold.y_px
            hold.x = x_px / surface.image_width_px if surface.image_width_px else hold.x
            hold.y = y_px / surface.image_height_px if surface.image_height_px else hold.y
        else:
            x_px, y_px = surface.normalized_to_pixel_coords(hold.x, hold.y)
            hold.x_px = x_px
            hold.y_px = y_px

        hold.x_m, hold.y_m = surface.pixel_to_surface_coords(hold.x_px, hold.y_px)

@router.post("/walls")
def save_wall(
    data: WallInput,
    session: Session = Depends(get_session)
):

    wall = Wall(gym_id=data.gym_id, image_name=data.image_name)
    session.add(wall)
    session.flush()

    surface = build_default_surface(wall.id, data)
    session.add(surface)
    session.commit()
    session.refresh(wall)
    session.refresh(surface)
    return {"status": "saved", "wall_id": wall.id, "surface_id": surface.id}

@router.get("/walls/{wall_id}")
def get_wall(
    wall_id: int,
    session: Session = Depends(get_session)
):

    wall = session.get(Wall, wall_id)
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")

    surfaces = list(wall.surfaces)
    surface_ids = [surface.id for surface in surfaces]
    holds = []
    if surface_ids:
        statement = select(Hold).where(Hold.surface_id.in_(surface_ids))
        holds = session.exec(statement).all()

    return {
        "id": wall.id,
        "gym_id": wall.gym_id,
        "image_name": wall.image_name,
        "surfaces": surfaces,
        "holds": holds,
    }


@router.post("/walls/{wall_id}/holds")
def add_holds(
    wall_id: int,
    data: HoldsInput,
    session: Session = Depends(get_session)
):
    wall = session.get(Wall, wall_id)
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")

    surface = wall.surfaces[0] if wall.surfaces else None
    if not surface:
        surface = build_default_surface(wall.id)
        session.add(surface)
        session.flush()

    for hold_data in data.holds:
        x, y, x_px, y_px, x_m, y_m = hold_coordinates(hold_data, surface)
        hold = Hold(
            surface_id=surface.id,
            x=x,
            y=y,
            z=0,
            x_px=x_px,
            y_px=y_px,
            x_m=x_m,
            y_m=y_m,
            hold_type=hold_data.hold_type,
            size=hold_data.size,
        ) 
        session.add(hold)
    session.commit()    

    session.refresh(wall)
    return {'id': wall.id, "holds": wall.all_holds() }


@router.patch("/surfaces/{surface_id}/geometry")
def update_surface_geometry(
    surface_id: int,
    data: SurfaceGeometryInput,
    session: Session = Depends(get_session),
):
    surface = session.get(Surface, surface_id)
    if not surface:
        raise HTTPException(status_code=404, detail="Surface not found")

    surface.width_m = data.width_m
    surface.height_m = data.height_m
    surface.image_width_px = data.image_width_px
    surface.image_height_px = data.image_height_px
    surface.width = data.width_m
    surface.height = data.height_m
    if data.angle is not None:
        surface.angle = data.angle

    recalculate_surface_holds(surface)
    session.add(surface)
    session.commit()
    session.refresh(surface)

    return {"status": "saved", "surface": surface, "holds": surface.holds}


@router.delete("/walls/{wall_id}/holds/{hold_id}")
def delete_hold(
    wall_id: int,
    hold_id: int,
    session: Session = Depends(get_session),
):
    wall = session.get(Wall, wall_id)
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")

    surface_ids = [surface.id for surface in wall.surfaces]
    hold = session.get(Hold, hold_id)
    if not hold or hold.surface_id not in surface_ids:
        raise HTTPException(status_code=404, detail="Hold not found")

    session.delete(hold)
    session.commit()
    return {"status": "deleted"}
