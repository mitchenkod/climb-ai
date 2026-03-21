from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from backend.db import get_session
from backend.models.wall import Wall
from backend.models.hold import Hold
from pydantic import BaseModel
from typing import List

router = APIRouter()

class WallInput(BaseModel):
    gym_id: int

class HoldInput(BaseModel):
    x: float
    y: float
    hold_type: str

class HoldsInput(BaseModel):
    holds: List[HoldInput]

@router.post("/walls")
def save_wall(
    data: WallInput,
    session: Session = Depends(get_session)
):

    wall = Wall(gym_id=data.gym_id)
    session.add(wall)
    session.commit()
    session.refresh(wall)
    return {"status": "saved", "wall_id": wall.id}

@router.get("/walls/{wall_id}")
def get_wall(
    wall_id: int,
    session: Session = Depends(get_session)
):

    wall = session.get(Wall, wall_id)
    statement = select(Hold)
    holds = session.exec(statement).all()

    return {'id': wall.id, "holds": holds }


@router.post("/walls/{wall_id}/holds")
def add_holds(
    wall_id: int,
    data: HoldsInput,
    session: Session = Depends(get_session)
):
    wall = session.get(Wall, wall_id)
    for hold_data in data.holds:
        hold = Hold(
            wall_id=wall_id,
            x=hold_data.x,
            y=hold_data.y,
            z=0,
            hold_type=hold_data.hold_type
        ) 
        session.add(hold)
    session.commit()    

    return {'id': wall.id, "holds": wall.all_holds() }