from typing import List, Optional
from sqlmodel import Relationship, Field
from .base import BaseTable

class Route(BaseTable, table=True):
    name: str
    wall_id: Optional[int] = Field(default=None, foreign_key="wall.id")

    difficulty_score: Optional[float] = None

    holds_in_route: List["HoldInRoute"] = Relationship(
        back_populates="route"
    )
