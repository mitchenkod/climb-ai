import sys
from pathlib import Path
from typing import List, Optional

# Добавить корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.models.surface import Surface
from backend.models.route import Route
from backend.models.movement_graph import MovementGraph as MovementGraphModel
from backend.models.hold_in_route import HoldInRoute
from backend.models.hold import Hold
from backend.models.graph import MovementGraph, Movement, MovementHold, BodyPosition
from backend.db import get_session
import random
from itertools import combinations

MIN_START_Y = 0.0
MAX_START_Y = 2.0

MIN_HAND_FOOT_GAP = 0.3  # руки выше ног


class RouteBuilder:
    def __init__(self, session=None):
        self.session = session

    def build_route_from_surface(self, surface: Surface, route_name: str = "auto_route"):
        """Главный метод: создаёт route + movement graph + стартовую позицию"""
        holds = list(surface.holds)

        route = Route(name=route_name, wall_id=surface.wall_id if hasattr(surface, 'wall_id') else None)
        if self.session:
            self.session.add(route)

        movement_graph = MovementGraphModel(route=route)
        if self.session:
            self.session.add(movement_graph)

        start_holds = self.select_start_holds(holds)
        if start_holds:
            self.set_start_holds(route, start_holds)
            start_position = self.create_body_position_for_holds(start_holds)
        else:
            start_position = None

        if self.session:
            self.session.commit()

        return {
            "route": route,
            "movement_graph": movement_graph,
            "start_position": start_position,
            "start_holds": start_holds,
        }

    def create_start_position(self, holds: List[Hold]) -> List[Hold]:
        """Определяет стартовые 4 зацепки. Пока заглушка, можно переопределить."""
        raise NotImplementedError("Метод create_start_position должен быть реализован")

    def select_start_state(all_holds, max_attempts=100):
        # 1. фильтруем стартовую зону
        candidates = [
            h for h in all_holds
            if MIN_START_Y <= h["y"] <= MAX_START_Y
        ]

        if len(candidates) < 4:
            return None

        for _ in range(max_attempts):

            # 2. случайно берём 4 holds
            selected = random.sample(candidates, 4)

            # 3. делим на "ноги" и "руки" по высоте
            sorted_holds = sorted(selected, key=lambda h: h["y"])

            feet = sorted_holds[:2]
            hands = sorted_holds[2:]

            # 4. проверка: руки выше ног
            if min(h["y"] for h in hands) - max(h["y"] for h in feet) < MIN_HAND_FOOT_GAP:
                continue

            # 5. геометрическая проверка
            if not is_assignable(selected):
                continue

            # 6. дополнительная эвристика: ширина ног
            foot_span = distance(feet[0], feet[1])
            if foot_span < 0.2:  # слишком узко
                continue

            # 7. дополнительная эвристика: руки не слишком далеко
            hand_span = distance(hands[0], hands[1])
            if hand_span > 1.5:
                continue

            return selected

        return None

    def select_start_holds(self, holds: List[Hold]) -> List[Hold]:
        """По умолчанию: берем 4 верхних зацепа (как в generate_route)."""
        if not holds:
            return []

        ordered = sorted(holds, key=lambda h: h.y, reverse=True)
        selected = ordered[:4]
        return selected

    def set_start_holds(self, route: Route, start_holds: List[Hold]):
        """Добавляет стартовые зацепы в маршрут."""
        for h in start_holds:
            HoldInRoute(route=route, hold=h, role='start')

    def create_body_position_for_holds(self, holds: List[Hold]) -> BodyPosition:
        """Создает Movement + BodyPosition для заданных зацепов"""
        signature = ",".join(str(h.id) for h in sorted(holds, key=lambda h: h.id))
        movement = Movement(signature=signature)

        for h in holds:
            association = MovementHold(movement=movement, hold=h)
            if self.session:
                self.session.add(association)

        center_position = BodyPosition(
            from_movement=movement,
            to_movement=movement,
            moved_hand='L',
            cost=0.0,
        )

        if self.session:
            self.session.add(movement)
            self.session.add(center_position)

        return center_position


def build_route_for_surface(surface: Surface, session=None, route_name: str = "auto_route"):
    builder = RouteBuilder(session=session)
    return builder.build_route_from_surface(surface, route_name=route_name)
