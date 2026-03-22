import sys
from pathlib import Path

# Добавить корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.models.graph import Movement, MovementHold, MovementGraph, BodyPosition
from sqlmodel import select 
from backend.models.hold import Hold
from typing import Dict, List
from itertools import combinations
from backend.db import get_session

def main():
    print("Building movement graph...")
    for session in get_session():
        create_movement_graph(session.exec(select(Hold)).all(), max_contacts=4, distance_threshold=0.1)
        break


def create_movement_graph(holds, max_contacts=4, distance_threshold=0.1):
    graph = MovementGraph()
    hold_ids = [h.id for h in holds]
    hold_map = {h.id: h for h in holds}

    print(f"Total holds: {len(holds)}, hold IDs: {hold_ids}")
    
    # Ищем движения: для каждого hold берем близкие к нему holds (в пределах distance_threshold)
    nodes = []
    created_signatures = set()  # Избегаем дубликатов
    
    for anchor_hold in holds:
        # Найти все holds в пределе distance_threshold от текущего
        nearby_holds = []
        for h in holds:
            # Вычисляем 3D расстояние между захватами
            distance = ((h.x - anchor_hold.x)**2 + (h.y - anchor_hold.y)**2 + (h.z - anchor_hold.z)**2)**0.5
            print(f"Distance from hold {anchor_hold.id} to hold {h.id}: {distance:.3f}")
            if distance <= distance_threshold:
                nearby_holds.append(h.id)
        
        print(f"Hold {anchor_hold.id}: found {len(nearby_holds)} nearby holds within {distance_threshold}")
        
        # Создать комбинации из близких holds (от 1 до max_contacts)
        for k in range(2, min(max_contacts, len(nearby_holds)) + 1):
            for c in combinations(nearby_holds, k):
                signature = ",".join(str(x) for x in sorted(c))
                
                # Пропускаем уже созданные движения
                if signature not in created_signatures:
                    print(f"Creating movement for holds: {c}, signature: {signature}")
                    nodes.append(Movement(signature=signature))
                    created_signatures.add(signature)

    print(f"Created {len(nodes)} unique nodes")
    
    for node in nodes:
        graph.add_node(node)

    # переходы (BodyPosition)
    for node in nodes:
        for h_out in node.holds:
            for h_in in hold_ids:
                if h_in in node.holds:
                    continue

                new_holds = list(node.holds)
                new_holds.remove(h_out)
                new_holds.append(h_in)

                signature = ",".join(str(x) for x in sorted(new_holds))
                new_node = Movement(signature=signature)

                cost = compute_transition_cost()
                print(f"Computing transition cost for transition: {node.holds} -> {new_holds}, cost: {cost}")

                if cost is None:
                    continue

                edge = BodyPosition(
                    from_movement=node,
                    to_movement=new_node,
                    moved_hand="L",
                    cost=cost,
                )
                graph.add_edge(edge)

    return graph, nodes, hold_map

def compute_transition_cost():
    return 1.0  # заглушка, реальная логика будет сложнее

def get_or_create_movement(session, hold_ids):
    signature = make_signature(hold_ids)

    movement = session.exec(
        select(Movement).where(Movement.signature == signature)
    ).first()

    if movement:
        return movement

    movement = Movement(signature=signature)
    session.add(movement)
    session.commit()
    session.refresh(movement)

    for hid in hold_ids:
        session.add(MovementHold(movement_id=movement.id, hold_id=hid))

    session.commit()

    return movement


def make_signature(hold_ids):
    sorted_ids = sorted(hold_ids)
    return ",".join(map(str, sorted_ids))       


def assign_limbs(holds):
    """
    holds: List[Hold]
    возвращает:
    {
        "left_hand": Hold | None,
        "right_hand": Hold | None,
        "left_foot": Hold | None,
        "right_foot": Hold | None,
    }
    """

    if not holds:
        return {}

    # сортируем по высоте
    sorted_by_y = sorted(holds, key=lambda h: h.pos[1])

    feet = sorted_by_y[:2]
    hands = sorted_by_y[-2:] if len(holds) > 2 else sorted_by_y

    def split_lr(group):
        if len(group) == 1:
            return group[0], None

        group_sorted = sorted(group, key=lambda h: h.pos[0])
        return group_sorted[0], group_sorted[-1]

    left_foot, right_foot = split_lr(feet)
    left_hand, right_hand = split_lr(hands)

    return {
        "left_hand": left_hand,
        "right_hand": right_hand,
        "left_foot": left_foot,
        "right_foot": right_foot,
    }

if __name__ == "__main__":
    main()
