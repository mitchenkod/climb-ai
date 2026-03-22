from typing import List, Optional, Dict
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship
from .base import BaseTable
from .hold import Hold


class MovementHold(BaseTable, table=True):
    """Связь между движением и захватом (many-to-many)"""
    movement_id: Optional[int] = Field(default=None, foreign_key="movement.id")
    hold_id: Optional[int] = Field(default=None, foreign_key="hold.id")
    
    movement: Mapped[Optional["Movement"]] = Relationship(back_populates="holds_association")
    hold: Mapped[Optional["Hold"]] = Relationship()


class Movement(BaseTable, table=True):
    holds_association: Mapped[List["MovementHold"]] = Relationship(back_populates="movement")
    signature: str = Field(index=True, unique=True)

    @property
    def holds(self) -> List["Hold"]:
        """Получить все захваты для этого движения"""
        return [assoc.hold for assoc in self.holds_association if assoc.hold]


class BodyPosition(BaseTable, table=True):
    """
    Перехват одной руки (переход между движениями).
    """
    from_movement_id: Optional[int] = Field(default=None, foreign_key="movement.id")
    to_movement_id: Optional[int] = Field(default=None, foreign_key="movement.id")

    from_movement: Mapped[Optional["Movement"]] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[BodyPosition.from_movement_id]",
            "primaryjoin": "BodyPosition.from_movement_id==Movement.id"
        }
    )
    to_movement: Mapped[Optional["Movement"]] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[BodyPosition.to_movement_id]",
            "primaryjoin": "BodyPosition.to_movement_id==Movement.id"
        }
    )

    moved_hand: str  # "L" или "R"
    cost: float


class MovementGraph:
    def __init__(self):
        # Используем signature как ключ вместо объекта Movement
        self.nodes: Dict[str, List[BodyPosition]] = {}

    def add_node(self, node: Movement):
        if node.signature not in self.nodes:
            self.nodes[node.signature] = []

    def add_edge(self, edge: BodyPosition):
        self.add_node(edge.from_movement)
        self.add_node(edge.to_movement)
        self.nodes[edge.from_movement.signature].append(edge)

    def neighbors(self, node: Movement) -> List[BodyPosition]:
        return self.nodes.get(node.signature, [])


# Сохранение обратной совместимости с прежними именами
GraphNodeHold = MovementHold
GraphNode = Movement
GraphEdge = BodyPosition