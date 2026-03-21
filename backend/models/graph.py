from typing import List, Optional, Dict
from sqlmodel import Field, Relationship
from .base import BaseTable


class GraphNodeHold(BaseTable, table=True):
    """Связь между вершиной графа и захватом (many-to-many)"""
    graph_node_id: Optional[int] = Field(default=None, foreign_key="graphnode.id")
    hold_id: Optional[int] = Field(default=None, foreign_key="hold.id")
    
    graph_node: Optional["GraphNode"] = Relationship(back_populates="holds_association")
    hold: Optional["Hold"] = Relationship()


class GraphNode(BaseTable, table=True):
    holds_association: List["GraphNodeHold"] = Relationship(back_populates="graph_node")
    signature: str = Field(index=True, unique=True)
    
    @property
    def holds(self) -> List["Hold"]:
        """Получить все захваты для этой вершины"""
        return [assoc.hold for assoc in self.holds_association if assoc.hold]


class GraphEdge(BaseTable, table=True):
    """
    Перехват одной руки.
    """
    from_node_id: Optional[int] = Field(default=None, foreign_key="graphnode.id")
    to_node_id: Optional[int] = Field(default=None, foreign_key="graphnode.id")
    
    from_node: Optional["GraphNode"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[GraphEdge.from_node_id]",
            "primaryjoin": "GraphEdge.from_node_id==GraphNode.id"
        }
    )
    to_node: Optional["GraphNode"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[GraphEdge.to_node_id]",
            "primaryjoin": "GraphEdge.to_node_id==GraphNode.id"
        }
    )
    
    moved_hand: str  # "L" или "R"
    cost: float


class MovementGraph:
    def __init__(self):
        # Используем signature как ключ вместо объекта GraphNode
        self.nodes: Dict[str, List[GraphEdge]] = {}

    def add_node(self, node: GraphNode):
        if node.signature not in self.nodes:
            self.nodes[node.signature] = []

    def add_edge(self, edge: GraphEdge):
        self.add_node(edge.from_node)
        self.add_node(edge.to_node)
        self.nodes[edge.from_node.signature].append(edge)

    def neighbors(self, node: GraphNode) -> List[GraphEdge]:
        return self.nodes.get(node.signature, [])