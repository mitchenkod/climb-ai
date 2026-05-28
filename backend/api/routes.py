from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlmodel import Session, select
from itertools import combinations
import random
from backend.db import get_session
from backend.models.hold import Hold
from backend.models.hold_in_route import HoldInRoute, HoldRole
from backend.models.movement_graph import MovementGraph as MovementGraphModel
from backend.models.route import Route
from backend.models.surface import Surface
from backend.models.wall import Wall
from backend.services.climbing.body_position import (
    BodyPositionScore,
    hold_point,
    score_body_position,
)
from backend.services.climbing.route_builder import build_route_for_surface
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Sequence, Tuple

router = APIRouter()

class RouteInput(BaseModel):
    wall_id: Optional[int] = None
    surface_id: Optional[int] = None
    name: str = "auto_route"


TOP_ROW_HEIGHT_RATIO = 0.1
MIN_NEXT_HAND_GAIN_M = 0.05
MAX_NEXT_HAND_CANDIDATES = 30
ATTACH_FOOT_FROM_CANDIDATE_INDEX = 2
ATTACH_FOOT_PROBABILITY = 0.3
MAX_PREVIOUS_POSITION_FOOT_IMPROVEMENT = 0.35
MAX_ATTACHED_FOOT_CANDIDATES = 12


def serialize_route(route: Route, session: Session) -> Dict[str, Any]:
    holds_in_route = session.exec(
        select(HoldInRoute)
        .where(HoldInRoute.route_id == route.id)
        .order_by(HoldInRoute.order_index)
    ).all()
    route_holds = [
        serialize_hold_in_route(hold_in_route)
        for hold_in_route in holds_in_route
        if hold_in_route.hold
    ]
    start_holds = [
        item["hold"]
        for item in route_holds
        if item["role"] == HoldRole.START.value
    ]

    return {
        "route_id": route.id,
        "name": route.name,
        "wall_id": route.wall_id,
        "difficulty_score": route.difficulty_score,
        "created_at": route.created_at.isoformat(),
        "holds": route_holds,
        "start_holds": start_holds,
    }


def serialize_hold(hold: Hold) -> Dict[str, Any]:
    return {
        "id": hold.id,
        "x": hold.x,
        "y": hold.y,
        "x_px": hold.x_px,
        "y_px": hold.y_px,
        "hold_type": hold.hold_type,
        "quality": hold.quality,
        "force_vectors": hold.force_vectors,
    }


def serialize_hold_in_route(hold_in_route: HoldInRoute) -> Dict[str, Any]:
    hold = hold_in_route.hold
    return {
        "role": hold_in_route.role.value if isinstance(hold_in_route.role, HoldRole) else hold_in_route.role,
        "order_index": hold_in_route.order_index,
        "start_limb_count": hold_in_route.start_limb_count,
        "hold": serialize_hold(hold),
    }


def serialize_position_score(score: BodyPositionScore, hands: Sequence[Hold], feet: Sequence[Hold]) -> Dict[str, Any]:
    return {
        "score": score.score,
        "is_realistic": score.is_realistic,
        "hands": [serialize_hold(hold) for hold in hands],
        "feet": [serialize_hold(hold) for hold in feet],
        "holds": [serialize_hold(hold) for hold in score.holds],
        "breakdown": score.breakdown,
        "weighted_breakdown": score.weighted_breakdown,
        "weights": score.weights,
    }


def route_hold_links(route_id: int, session: Session) -> List[HoldInRoute]:
    return session.exec(
        select(HoldInRoute)
        .where(HoldInRoute.route_id == route_id)
        .order_by(HoldInRoute.order_index)
    ).all()


def route_has_finish(links: Sequence[HoldInRoute]) -> bool:
    return any(link.role == HoldRole.FINISH for link in links)


def current_hand_holds(links: Sequence[HoldInRoute]) -> List[Hold]:
    hand_links = [
        link for link in links
        if link.hold and link.role in {HoldRole.START, HoldRole.INTERMEDIATE, HoldRole.FINISH}
        and link.hold.hold_type != "foot"
    ]
    if not hand_links:
        return []

    intermediate_links = [
        link for link in hand_links
        if link.role in {HoldRole.INTERMEDIATE, HoldRole.FINISH}
    ]
    if intermediate_links:
        latest = intermediate_links[-1].hold
        previous_candidates = [
            link.hold for link in hand_links[:-1]
            if link.hold and link.hold.id != latest.id
        ]
        if not previous_candidates:
            return [latest]
        previous = max(previous_candidates, key=lambda hold: hold_point(hold)[1])
        return sorted([previous, latest], key=lambda hold: hold_point(hold)[0])

    start_holds = [link.hold for link in hand_links if link.hold]
    return sorted(start_holds, key=lambda hold: hold_point(hold)[1])[-2:]


def wall_holds(wall: Wall, session: Session) -> List[Hold]:
    surface_ids = [surface.id for surface in wall.surfaces]
    if not surface_ids:
        return []
    return session.exec(
        select(Hold).where(Hold.surface_id.in_(surface_ids))
    ).all()


def top_row_threshold(holds: Sequence[Hold]) -> float:
    if not holds:
        return 0.0
    min_y = min(hold_point(hold)[1] for hold in holds)
    max_y = max(hold_point(hold)[1] for hold in holds)
    return max_y - (max_y - min_y) * TOP_ROW_HEIGHT_RATIO


def next_hand_candidates(
    holds: Sequence[Hold],
    current_hands: Sequence[Hold],
    route_links: Sequence[HoldInRoute],
) -> List[Hold]:
    used_hold_ids = {
        link.hold_id
        for link in route_links
        if link.hold_id is not None
    }
    current_max_y = max(hold_point(hold)[1] for hold in current_hands)
    candidates = [
        hold for hold in holds
        if hold.id not in used_hold_ids
        and hold.hold_type != "foot"
        and hold_point(hold)[1] > current_max_y + MIN_NEXT_HAND_GAIN_M
    ]
    candidates.sort(key=lambda hold: (
        hold_point(hold)[1],
        -min(abs(hold_point(hold)[0] - hold_point(hand)[0]) for hand in current_hands),
    ))
    return candidates[:MAX_NEXT_HAND_CANDIDATES]


def choose_next_move_position(
    route_holds: Sequence[Hold],
    current_hands: Sequence[Hold],
    new_hand: Hold,
    wall_angle_deg: float,
) -> Optional[Tuple[BodyPositionScore, List[Hold], List[Hold]]]:
    best: Optional[Tuple[BodyPositionScore, List[Hold], List[Hold]]] = None
    foot_pool = [
        hold for hold in route_holds
        if hold.id not in {new_hand.id, *(hand.id for hand in current_hands)}
        and hold_point(hold)[1] < hold_point(new_hand)[1]
    ]

    for old_hand in current_hands:
        hands = [old_hand, new_hand]
        candidate_feet = [
            foot for foot in foot_pool
            if foot.id not in {hand.id for hand in hands}
            and hold_point(foot)[1] < min(hold_point(hand)[1] for hand in hands)
        ]
        for feet in combinations(candidate_feet, 2):
            position_holds = [*feet, *hands]
            score = score_body_position(
                position_holds,
                wall_angle_deg=wall_angle_deg,
            )
            if not score.is_realistic:
                continue
            option = (score, hands, list(feet))
            if best is None or score.score < best[0].score:
                best = option

    return best


def poor_new_foot_candidates(
    holds: Sequence[Hold],
    route_holds: Sequence[Hold],
    current_hands: Sequence[Hold],
    new_hand: Hold,
) -> List[Hold]:
    used_hold_ids = {hold.id for hold in route_holds}
    used_hold_ids.add(new_hand.id)
    min_hand_y = min(hold_point(hold)[1] for hold in [*current_hands, new_hand])
    candidates = [
        hold for hold in holds
        if hold.id not in used_hold_ids
        and hold_point(hold)[1] < min_hand_y
    ]
    candidates.sort(key=lambda hold: (
        0 if hold.hold_type == "foot" else 1,
        hold.quality,
        -hold_point(hold)[1],
    ))
    return candidates[:MAX_ATTACHED_FOOT_CANDIDATES]


def choose_next_move_with_attached_foot(
    holds: Sequence[Hold],
    route_holds: Sequence[Hold],
    previous_hands: Sequence[Sequence[Hold]],
    current_hands: Sequence[Hold],
    new_hand: Hold,
    wall_angle_deg: float,
) -> Optional[Tuple[BodyPositionScore, List[Hold], List[Hold], Hold]]:
    best: Optional[Tuple[BodyPositionScore, List[Hold], List[Hold], Hold]] = None
    for foot in poor_new_foot_candidates(holds, route_holds, current_hands, new_hand):
        if improves_previous_positions_too_much(route_holds, previous_hands, foot, wall_angle_deg):
            continue

        option = choose_next_move_position(
            [*route_holds, foot],
            current_hands,
            new_hand,
            wall_angle_deg,
        )
        if option is None:
            continue

        score, hands, feet = option
        if foot not in feet:
            continue
        candidate = (score, hands, feet, foot)
        if best is None or score.score < best[0].score:
            best = candidate

    return best


def improves_previous_positions_too_much(
    route_holds: Sequence[Hold],
    previous_hands: Sequence[Sequence[Hold]],
    new_foot: Hold,
    wall_angle_deg: float,
) -> bool:
    for hands in previous_hands:
        base = choose_best_feet_for_hands(route_holds, hands, wall_angle_deg)
        improved = choose_best_feet_for_hands([*route_holds, new_foot], hands, wall_angle_deg)
        if base is None or improved is None:
            continue
        if base.score - improved.score > MAX_PREVIOUS_POSITION_FOOT_IMPROVEMENT:
            return True
    return False


def previous_hand_pairs(links: Sequence[HoldInRoute]) -> List[List[Hold]]:
    hand_holds = [
        link.hold for link in links
        if link.hold
        and link.role in {HoldRole.START, HoldRole.INTERMEDIATE, HoldRole.FINISH}
        and link.hold.hold_type != "foot"
    ]
    if len(hand_holds) < 2:
        return []

    pairs: List[List[Hold]] = []
    current = sorted(hand_holds[:2], key=lambda hold: hold_point(hold)[0])
    pairs.append(current)
    for new_hand in hand_holds[2:]:
        previous = max(current, key=lambda hold: hold_point(hold)[1])
        current = sorted([previous, new_hand], key=lambda hold: hold_point(hold)[0])
        pairs.append(current)
    return pairs


def choose_best_feet_for_hands(
    available_holds: Sequence[Hold],
    hands: Sequence[Hold],
    wall_angle_deg: float,
) -> Optional[BodyPositionScore]:
    foot_pool = [
        hold for hold in available_holds
        if hold.id not in {hand.id for hand in hands}
        and hold_point(hold)[1] < min(hold_point(hand)[1] for hand in hands)
    ]
    best: Optional[BodyPositionScore] = None
    for feet in combinations(foot_pool, 2):
        score = score_body_position([*feet, *hands], wall_angle_deg=wall_angle_deg)
        if not score.is_realistic:
            continue
        if best is None or score.score < best.score:
            best = score
    return best


def route_available_holds(links: Sequence[HoldInRoute]) -> List[Hold]:
    by_id: Dict[int, Hold] = {}
    for link in links:
        if link.hold and link.hold.id is not None:
            by_id[link.hold.id] = link.hold
    return list(by_id.values())


@router.post("/routes")
def create_route(
    data: RouteInput,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    if data.surface_id is not None:
        surface = session.get(Surface, data.surface_id)
    elif data.wall_id is not None:
        statement = select(Surface).where(Surface.wall_id == data.wall_id).limit(1)
        surface = session.exec(statement).first()
    else:
        raise HTTPException(status_code=400, detail="wall_id or surface_id is required")
    
    if not surface:
        raise HTTPException(status_code=404, detail="Surface not found")
    
    result = build_route_for_surface(surface, session=session, route_name=data.name)
    
    return {
        "route_id": result["route"].id,
        "difficulty_score": result["route"].difficulty_score,
        "movement_graph_id": result["movement_graph"].id,
        "start_position": result["start_position"].id if result["start_position"] else None,
        "start_holds": [
            {
                "id": h.id,
                "x": h.x,
                "y": h.y,
                "x_px": h.x_px,
                "y_px": h.y_px,
            }
            for h in result["start_holds"]
        ],
        "start_position_score": {
            "score": result["start_score"].score,
            "is_realistic": result["start_score"].is_realistic,
            "breakdown": result["start_score"].breakdown,
            "weighted_breakdown": result["start_score"].weighted_breakdown,
            "weights": result["start_score"].weights,
        } if result["start_score"] else None,
    }


@router.get("/walls/{wall_id}/routes")
def list_wall_routes(
    wall_id: int,
    page: int = 1,
    page_size: int = 10,
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    wall = session.get(Wall, wall_id)
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")

    page = max(1, page)
    page_size = min(50, max(1, page_size))
    total = session.exec(
        select(func.count())
        .select_from(Route)
        .where(Route.wall_id == wall_id)
    ).one()
    routes = session.exec(
        select(Route)
        .where(Route.wall_id == wall_id)
        .order_by(Route.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "wall_id": wall_id,
        "page": page,
        "page_size": page_size,
        "total": total,
        "routes": [serialize_route(route, session) for route in routes],
    }


@router.delete("/walls/{wall_id}/routes/{route_id}")
def delete_wall_route(
    wall_id: int,
    route_id: int,
    session: Session = Depends(get_session),
) -> Dict[str, str]:
    route = session.get(Route, route_id)
    if not route or route.wall_id != wall_id:
        raise HTTPException(status_code=404, detail="Route not found")

    hold_links = session.exec(
        select(HoldInRoute).where(HoldInRoute.route_id == route_id)
    ).all()
    for hold_link in hold_links:
        session.delete(hold_link)

    movement_graphs = session.exec(
        select(MovementGraphModel).where(MovementGraphModel.route_id == route_id)
    ).all()
    for movement_graph in movement_graphs:
        session.delete(movement_graph)

    session.delete(route)
    session.commit()
    return {"status": "deleted"}


@router.post("/walls/{wall_id}/route/{route_id}/next_move")
@router.post("/walls/{wall_id}/routes/{route_id}/next_move")
def add_next_move(
    wall_id: int,
    route_id: int,
    session: Session = Depends(get_session),
) -> Dict[str, Any]:
    wall = session.get(Wall, wall_id)
    if not wall:
        raise HTTPException(status_code=404, detail="Wall not found")

    route = session.get(Route, route_id)
    if not route or route.wall_id != wall_id:
        raise HTTPException(status_code=404, detail="Route not found")

    links = route_hold_links(route_id, session)
    if route_has_finish(links):
        raise HTTPException(status_code=409, detail="Route already has top hold")

    current_hands = current_hand_holds(links)
    if len(current_hands) < 2:
        raise HTTPException(status_code=409, detail="Route needs at least two current hand holds")

    holds = wall_holds(wall, session)
    if not holds:
        raise HTTPException(status_code=409, detail="Wall has no holds")

    surface = wall.surfaces[0] if wall.surfaces else None
    wall_angle_deg = surface.angle if surface else 0.0
    top_threshold = top_row_threshold(holds)
    route_holds = route_available_holds(links)
    previous_hands = previous_hand_pairs(links)
    best: Optional[Tuple[BodyPositionScore, List[Hold], List[Hold], Hold, Optional[Hold]]] = None

    for candidate_index, candidate in enumerate(next_hand_candidates(holds, current_hands, links)):
        option = choose_next_move_position(
            route_holds,
            current_hands,
            candidate,
            wall_angle_deg,
        )
        attached_foot = None
        if (
            candidate_index >= ATTACH_FOOT_FROM_CANDIDATE_INDEX
            and random.random() < ATTACH_FOOT_PROBABILITY
        ):
            attached_option = choose_next_move_with_attached_foot(
                holds,
                route_holds,
                previous_hands,
                current_hands,
                candidate,
                wall_angle_deg,
            )
            if attached_option and (option is None or attached_option[0].score < option[0].score):
                option = attached_option[:3]
                attached_foot = attached_option[3]

        if option is None:
            continue
        score, hands, feet = option
        if best is None or score.score < best[0].score:
            best = (score, hands, feet, candidate, attached_foot)

    if best is None:
        raise HTTPException(status_code=409, detail="No valid next move found")

    score, hands, feet, new_hand, attached_foot = best
    role = HoldRole.FINISH if hold_point(new_hand)[1] >= top_threshold else HoldRole.INTERMEDIATE
    next_order_index = max((link.order_index for link in links), default=-1) + 1
    if attached_foot is not None:
        session.add(HoldInRoute(
            route_id=route.id,
            hold_id=attached_foot.id,
            role=HoldRole.FOOT_SUGGESTED,
            order_index=next_order_index,
            start_limb_count=None,
        ))
        next_order_index += 1

    route_link = HoldInRoute(
        route_id=route.id,
        hold_id=new_hand.id,
        role=role,
        order_index=next_order_index,
        start_limb_count=None,
    )
    session.add(route_link)
    route.difficulty_score = score.score
    session.add(route)
    session.commit()
    session.refresh(route)

    route_payload = serialize_route(route, session)
    return {
        "route": route_payload,
        "new_hold": serialize_hold(new_hand),
        "attached_foot": serialize_hold(attached_foot) if attached_foot else None,
        "role": role.value,
        "next_position": serialize_position_score(score, hands=hands, feet=feet),
    }
