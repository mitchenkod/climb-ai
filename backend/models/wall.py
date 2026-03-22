from typing import Optional, List, TYPE_CHECKING
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship
from .base import BaseTable

if TYPE_CHECKING:
    from .gym import Gym
    from .surface import Surface

class Wall(BaseTable, table=True):
    gym_id: Optional[int] = Field(default=None, foreign_key="gym.id")

    gym: Mapped[Optional["Gym"]] = Relationship(back_populates="walls")
    surfaces: Mapped[List["Surface"]] = Relationship(back_populates="wall")

    def add_plane(self, surface):
        self.surfaces.append(surface)

    def all_holds(self):
        """Возвращает все зацепки со всех поверхностей стены"""
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