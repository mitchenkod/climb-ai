from typing import List, Optional
from sqlmodel import Field, Relationship
from .base import BaseTable

class MovementGraph(BaseTable, table=True):
    wall_id: Optional[int] = Field(default=None, foreign_key="wall.id")
