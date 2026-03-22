from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship
from .base import BaseTable

if TYPE_CHECKING:
    from .route import Route

class MovementGraph(BaseTable, table=True):
    route_id: Optional[int] = Field(default=None, foreign_key="route.id")
    route: Mapped[Optional["Route"]] = Relationship(back_populates="movement_graphs")
