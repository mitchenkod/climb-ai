from sqlmodel import SQLModel
from typing import Optional

class Plane(SQLModel):
    id: int
    wall_id: int
    normal_vector: Optional[list] = None  # [x, y, z]
    offset: Optional[float] = None
    def add_hold(self, hold):
        hold.plane = self
        self.holds.append(hold)