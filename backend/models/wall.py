from typing import Optional, List
from sqlmodel import Field, Relationship
from .base import BaseTable

class Wall(BaseTable, table=True):
    name: str

    gym_id: Optional[int] = Field(default=None, foreign_key="gym.id")

    gym: Optional["Gym"] = Relationship(back_populates="walls")
    surfaces: List["Surface"] = Relationship(back_populates="wall")

    def add_plane(self, surface):
        self.surfaces.append(surface)

    def all_holds(self):
        """Возвращает список всех зацепок со всех плоскостей"""
        holds = []
        for surface in self.surfaces:
            holds.extend(surface.holds)
        return holds

    def reachable_holds(self, hold, max_dist=0.3):
        """Возвращает зацепки, до которых можно дотянуться с текущей"""
        reachable = []
        hx, hy, hz = hold.world_coords()
        for other in self.all_holds():
            ox, oy, oz = other.world_coords()
            dist = ((hx - ox)**2 + (hy - oy)**2 + (hz - oz)**2)**0.5
            if dist <= max_dist and other.id != hold.id:
                reachable.append(other)
        return reachable