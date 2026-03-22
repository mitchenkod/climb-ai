from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship
from .base import BaseTable

if TYPE_CHECKING:
    from .wall import Wall

class Gym(BaseTable, table=True):
    name: str
    city: Optional[str] = None

    walls: Mapped[List["Wall"]] = Relationship(back_populates="gym")

    def all_holds(self):
        """
        Возвращает список всех зацепок всех стен
        """
        holds = []
        for wall in self.walls:
            holds.extend(wall.all_holds())
        return holds
