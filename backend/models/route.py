from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped
from sqlmodel import Relationship, Field
from .base import BaseTable
from .hold_in_route import HoldInRoute

if TYPE_CHECKING:
    from .movement_graph import MovementGraph

class Route(BaseTable, table=True):
    name: str
    wall_id: Optional[int] = Field(default=None, foreign_key="wall.id")

    difficulty_score: Optional[float] = None

    holds_in_route: Mapped[List["HoldInRoute"]] = Relationship(
        back_populates="route"
    )

    movement_graphs: Mapped[List["MovementGraph"]] = Relationship(back_populates="route")
