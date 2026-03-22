from typing import Optional, TYPE_CHECKING
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship
from .base import BaseTable
from enum import Enum

if TYPE_CHECKING:
    from .route import Route
    from .hold import Hold

class HoldRole(str, Enum):
    START = "start"
    INTERMEDIATE = "intermediate"
    FINISH = "finish"
    FOOT_SUGGESTED = "foot_suggested"
    OPTIONAL = "optional"

class HoldInRoute(BaseTable, table=True):
    route_id: Optional[int] = Field(default=None, foreign_key="route.id")
    hold_id: Optional[int] = Field(default=None, foreign_key="hold.id")

    order_index: int

    role: HoldRole

    start_limb_count: Optional[int] = None
    # только если role == "start"
    # 1-4 конечности без уточнения типа

    beta_hint: Optional[str] = None

    route: Mapped[Optional["Route"]] = Relationship(back_populates="holds_in_route")
    hold: Mapped[Optional["Hold"]] = Relationship(back_populates="routes")
