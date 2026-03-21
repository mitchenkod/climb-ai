from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from backend.db import get_session
from backend.models.gym import Gym
from pydantic import BaseModel
from typing import List

router = APIRouter()

class GymInput(BaseModel):
    name: str

@router.post("/gym")
def save_gym(
    data: GymInput,
    session: Session = Depends(get_session)
):
    statement = select(Gym).where(Gym.name == data.name)
    gym = session.exec(statement).first()

    if not gym:
        gym = Gym(name=data.name)
        session.add(gym)
        session.commit()
        session.refresh(gym)
    session.commit()
    return {"status": "saved"}

@router.get("/gyms")
def get_gyms(
    session: Session = Depends(get_session)
):

    statement = select(Gym)
    gyms = session.exec(statement).all()

    return gyms
