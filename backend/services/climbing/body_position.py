import json
import math
import random
from dataclasses import dataclass
from itertools import combinations
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from backend.models.hold import Hold


@dataclass(frozen=True)
class BodyPositionWeights:
    average_center_distance: float = 1.0
    max_center_distance: float = 1.2
    hand_foot_distance: float = 1.3
    angle_compact_stretched: float = 1.4
    triangle_rule: float = 1.1
    hold_quality: float = 1.4
    force_alignment: float = 1.0
    contact_count: float = 0.6

    def as_dict(self) -> Dict[str, float]:
        return {
            "average_center_distance": self.average_center_distance,
            "max_center_distance": self.max_center_distance,
            "hand_foot_distance": self.hand_foot_distance,
            "angle_compact_stretched": self.angle_compact_stretched,
            "triangle_rule": self.triangle_rule,
            "hold_quality": self.hold_quality,
            "force_alignment": self.force_alignment,
            "contact_count": self.contact_count,
        }


@dataclass(frozen=True)
class BodyPositionScore:
    holds: List[Hold]
    score: float
    is_realistic: bool
    breakdown: Dict[str, float]
    weighted_breakdown: Dict[str, float]
    weights: Dict[str, float]


DEFAULT_WEIGHTS = BodyPositionWeights()
MAX_CONTACTS = 4
MAX_PAIR_DISTANCE_M = 2.25
MAX_FOOT_SPAN_M = 1.6
MAX_HAND_SPAN_M = 1.8
MAX_HANDS_PER_FOOT_PAIR = 14
MAX_FOOT_PAIRS = 60
START_SELECTION_POOL_SIZE = 12
START_SELECTION_SCORE_TOLERANCE = 0.35
IDEAL_AVERAGE_CENTER_DISTANCE_M = 0.55
IDEAL_MAX_CENTER_DISTANCE_M = 0.95
MIN_HAND_FOOT_GAP_M = 0.45
IDEAL_HAND_FOOT_GAP_M = 1.25
MAX_HAND_FOOT_GAP_M = 1.15
MAX_HAND_REACH_FROM_FOOT_M = 1.4
REALISTIC_SCORE_LIMIT = 4.0
MAX_START_FOOT_VERTICAL_OFFSET_M = 0.5
MIN_COMFORTABLE_HAND_FOOT_GAP_M = 0.65
MAX_COMFORTABLE_HAND_FOOT_GAP_M = 1.05
ANGLE_COMPACT_STRETCHED_PENALTY_AT_45_DEG = 1.0


def score_body_position(
    holds: Sequence[Hold],
    weights: BodyPositionWeights = DEFAULT_WEIGHTS,
    lowest_hold_y_m: Optional[float] = None,
    wall_angle_deg: float = 0.0,
) -> BodyPositionScore:
    selected = list(holds)
    if not 1 <= len(selected) <= MAX_CONTACTS:
        return BodyPositionScore(
            holds=selected,
            score=math.inf,
            is_realistic=False,
            breakdown={"invalid_contact_count": 1.0},
            weighted_breakdown={"invalid_contact_count": math.inf},
            weights=weights.as_dict(),
        )

    points = [hold_point(hold) for hold in selected]
    center = geometric_center(points)
    center_distances = [distance(point, center) for point in points]
    pair_distances = [distance(a, b) for a, b in combinations(points, 2)]
    max_pair_distance = max(pair_distances, default=0.0)

    average_center_distance = sum(center_distances) / len(center_distances)
    max_center_distance = max(center_distances, default=0.0)
    hands, feet = split_hands_and_feet(selected)
    if has_foot_hold_in_hands(hands):
        return invalid_body_position_score(
            selected,
            weights,
            reason="foot_hold_used_by_hand",
        )
    if start_feet_too_high(feet, lowest_hold_y_m, wall_angle_deg):
        return invalid_body_position_score(
            selected,
            weights,
            reason="start_feet_too_high",
        )
    if start_hands_too_high(hands, feet):
        return invalid_body_position_score(
            selected,
            weights,
            reason="start_hands_too_high",
        )
    if start_hand_reach_too_far(hands, feet):
        return invalid_body_position_score(
            selected,
            weights,
            reason="start_hand_reach_too_far",
        )

    breakdown = {
        "average_center_distance": ratio_penalty(
            average_center_distance,
            IDEAL_AVERAGE_CENTER_DISTANCE_M,
        ),
        "max_center_distance": ratio_penalty(
            max_center_distance,
            IDEAL_MAX_CENTER_DISTANCE_M,
        ),
        "hand_foot_distance": hand_foot_distance_penalty(hands, feet),
        "angle_compact_stretched": angle_compact_stretched_penalty(
            hands,
            feet,
            wall_angle_deg,
        ),
        "triangle_rule": triangle_rule_penalty(hands, feet),
        "hold_quality": hold_quality_penalty(selected),
        "force_alignment": force_alignment_penalty(selected, center),
        "contact_count": contact_count_penalty(len(selected)),
    }
    weight_map = weights.as_dict()
    weighted_breakdown = {
        name: value * weight_map[name]
        for name, value in breakdown.items()
    }
    score = sum(weighted_breakdown.values())
    is_realistic = max_pair_distance <= MAX_PAIR_DISTANCE_M and score <= REALISTIC_SCORE_LIMIT

    return BodyPositionScore(
        holds=selected,
        score=score,
        is_realistic=is_realistic,
        breakdown=breakdown,
        weighted_breakdown=weighted_breakdown,
        weights=weight_map,
    )


def select_best_body_position(
    holds: Iterable[Hold],
    max_contacts: int = MAX_CONTACTS,
    weights: BodyPositionWeights = DEFAULT_WEIGHTS,
    wall_angle_deg: float = 0.0,
    randomize: bool = False,
    rng: Optional[random.Random] = None,
    excluded_signatures: Optional[Iterable[Tuple[int, ...]]] = None,
) -> Optional[BodyPositionScore]:
    candidates = list(holds)
    if not candidates:
        return None

    scored_candidates: List[BodyPositionScore] = []
    lowest_hold_y_m = min(hold_point(hold)[1] for hold in candidates)
    for selected in start_position_candidates(
        candidates,
        lowest_hold_y_m=lowest_hold_y_m,
        wall_angle_deg=wall_angle_deg,
        max_contacts=max_contacts,
    ):
        scored = score_body_position(
            selected,
            weights=weights,
            lowest_hold_y_m=lowest_hold_y_m,
            wall_angle_deg=wall_angle_deg,
        )
        scored_candidates.append(scored)

    return choose_body_position_score(
        scored_candidates,
        randomize=randomize,
        rng=rng,
        excluded_signatures=excluded_signatures,
    )


def choose_body_position_score(
    scored_candidates: Sequence[BodyPositionScore],
    randomize: bool = False,
    rng: Optional[random.Random] = None,
    excluded_signatures: Optional[Iterable[Tuple[int, ...]]] = None,
) -> Optional[BodyPositionScore]:
    if not scored_candidates:
        return None

    candidates = [score for score in scored_candidates if score.is_realistic]
    if not candidates:
        candidates = list(scored_candidates)

    best_contact_count = max(len(score.holds) for score in candidates)
    candidates = [
        score for score in candidates
        if len(score.holds) == best_contact_count
    ]
    candidates.sort(key=lambda score: score.score)

    excluded = set(excluded_signatures or [])
    if excluded:
        fresh_candidates = [
            score for score in candidates
            if body_position_signature(score.holds) not in excluded
        ]
        if fresh_candidates:
            candidates = fresh_candidates

    if not randomize:
        return candidates[0]

    best_score = candidates[0].score
    score_limit = best_score + START_SELECTION_SCORE_TOLERANCE
    pool = [
        score for score in candidates[:START_SELECTION_POOL_SIZE]
        if score.score <= score_limit
    ]
    chooser = rng or random
    return chooser.choice(pool or candidates[:1])


def body_position_signature(holds: Sequence[Hold]) -> Tuple[int, ...]:
    return tuple(
        sorted(
            int(hold.id)
            for hold in holds
            if hold.id is not None
        )
    )


def start_position_candidates(
    holds: Sequence[Hold],
    lowest_hold_y_m: float,
    wall_angle_deg: float,
    max_contacts: int,
) -> Iterable[Tuple[Hold, ...]]:
    max_size = min(max_contacts, MAX_CONTACTS, len(holds))
    regular_holds = [hold for hold in holds if hold.hold_type != "foot"]

    if max_size >= 1:
        yield from ((hold,) for hold in regular_holds)

    if max_size < 2:
        return

    feet = [
        hold for hold in holds
        if vertical_offset_from_lowest(hold, lowest_hold_y_m, wall_angle_deg)
        <= MAX_START_FOOT_VERTICAL_OFFSET_M
    ]
    foot_pairs = ranked_foot_pairs(feet)

    if max_size >= 2:
        for foot in feet:
            for hand in nearby_hand_candidates([foot], regular_holds):
                yield (foot, hand)

    if max_size >= 3:
        for foot_pair in foot_pairs:
            for hand in nearby_hand_candidates(foot_pair, regular_holds):
                if hand not in foot_pair:
                    yield (*foot_pair, hand)

    if max_size >= 4:
        for foot_pair in foot_pairs:
            nearby_hands = nearby_hand_candidates(foot_pair, regular_holds)
            for hand_pair in combinations(nearby_hands, 2):
                if hand_pair[0] in foot_pair or hand_pair[1] in foot_pair:
                    continue
                if distance(hold_point(hand_pair[0]), hold_point(hand_pair[1])) > MAX_HAND_SPAN_M:
                    continue
                yield (*foot_pair, *hand_pair)


def ranked_foot_pairs(feet: Sequence[Hold]) -> List[Tuple[Hold, Hold]]:
    pairs = [
        pair for pair in combinations(feet, 2)
        if distance(hold_point(pair[0]), hold_point(pair[1])) <= MAX_FOOT_SPAN_M
    ]
    pairs.sort(key=lambda pair: (
        abs(distance(hold_point(pair[0]), hold_point(pair[1])) - 0.8),
        max(hold_point(pair[0])[1], hold_point(pair[1])[1]),
    ))
    return pairs[:MAX_FOOT_PAIRS]


def nearby_hand_candidates(
    feet: Sequence[Hold],
    regular_holds: Sequence[Hold],
) -> List[Hold]:
    if not feet:
        return list(regular_holds[:MAX_HANDS_PER_FOOT_PAIR])

    foot_points = [hold_point(hold) for hold in feet]
    foot_center = geometric_center(foot_points)
    max_foot_y = max(point[1] for point in foot_points)

    candidates = []
    for hold in regular_holds:
        if hold in feet:
            continue
        point = hold_point(hold)
        gap = point[1] - max_foot_y
        if gap < MIN_HAND_FOOT_GAP_M or gap > MAX_HAND_FOOT_GAP_M:
            continue
        if distance(point, foot_center) > MAX_PAIR_DISTANCE_M:
            continue
        candidates.append((hold, abs(gap - IDEAL_HAND_FOOT_GAP_M) + abs(point[0] - foot_center[0])))

    candidates.sort(key=lambda item: item[1])
    return [hold for hold, _score in candidates[:MAX_HANDS_PER_FOOT_PAIR]]


def invalid_body_position_score(
    holds: Sequence[Hold],
    weights: BodyPositionWeights,
    reason: str,
) -> BodyPositionScore:
    return BodyPositionScore(
        holds=list(holds),
        score=math.inf,
        is_realistic=False,
        breakdown={reason: 1.0},
        weighted_breakdown={reason: math.inf},
        weights=weights.as_dict(),
    )


def hold_point(hold: Hold) -> Tuple[float, float]:
    x = hold.x_m if hold.x_m is not None else hold.x
    if hold.y_m is not None:
        y = hold.y_m
    else:
        # Normalized UI coordinates are top-down; scoring uses bottom-up height.
        y = 1.0 - hold.y
    return (x, y)


def geometric_center(points: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def split_hands_and_feet(holds: Sequence[Hold]) -> Tuple[List[Hold], List[Hold]]:
    ordered = sorted(holds, key=lambda hold: hold_point(hold)[1])
    if len(ordered) >= 3:
        feet = ordered[:2]
        hands = ordered[2:]
    elif len(ordered) == 2:
        feet = ordered[:1]
        hands = ordered[1:]
    else:
        feet = []
        hands = ordered
    return hands, feet


def has_foot_hold_in_hands(hands: Sequence[Hold]) -> bool:
    return any(hold.hold_type == "foot" for hold in hands)


def start_feet_too_high(
    feet: Sequence[Hold],
    lowest_hold_y_m: Optional[float],
    wall_angle_deg: float,
) -> bool:
    if not feet or lowest_hold_y_m is None:
        return False

    return any(
        vertical_offset_from_lowest(hold, lowest_hold_y_m, wall_angle_deg)
        > MAX_START_FOOT_VERTICAL_OFFSET_M
        for hold in feet
    )


def vertical_offset_from_lowest(
    hold: Hold,
    lowest_hold_y_m: float,
    wall_angle_deg: float,
) -> float:
    surface_offset = max(0.0, hold_point(hold)[1] - lowest_hold_y_m)
    vertical_ratio = max(0.0, math.cos(math.radians(wall_angle_deg)))
    return surface_offset * vertical_ratio


def start_hands_too_high(hands: Sequence[Hold], feet: Sequence[Hold]) -> bool:
    if not hands or not feet:
        return False

    min_hand_y = min(hold_point(hold)[1] for hold in hands)
    max_foot_y = max(hold_point(hold)[1] for hold in feet)
    return min_hand_y - max_foot_y > MAX_HAND_FOOT_GAP_M


def start_hand_reach_too_far(hands: Sequence[Hold], feet: Sequence[Hold]) -> bool:
    if not hands or not feet:
        return False

    foot_points = [hold_point(hold) for hold in feet]
    for hand in hands:
        hand_point = hold_point(hand)
        nearest_foot_distance = min(
            distance(hand_point, foot_point)
            for foot_point in foot_points
        )
        if nearest_foot_distance > MAX_HAND_REACH_FROM_FOOT_M:
            return True
    return False


def ratio_penalty(value: float, ideal: float) -> float:
    if ideal <= 0:
        return 0.0
    return max(0.0, value / ideal - 1.0)


def hand_foot_distance_penalty(hands: Sequence[Hold], feet: Sequence[Hold]) -> float:
    if not hands or not feet:
        return 1.0

    min_hand_y = min(hold_point(hold)[1] for hold in hands)
    max_foot_y = max(hold_point(hold)[1] for hold in feet)
    gap = min_hand_y - max_foot_y
    if gap < MIN_HAND_FOOT_GAP_M:
        return (MIN_HAND_FOOT_GAP_M - gap) / MIN_HAND_FOOT_GAP_M
    if gap > MAX_HAND_FOOT_GAP_M:
        return (gap - MAX_HAND_FOOT_GAP_M) / IDEAL_HAND_FOOT_GAP_M
    return abs(gap - IDEAL_HAND_FOOT_GAP_M) / IDEAL_HAND_FOOT_GAP_M


def angle_compact_stretched_penalty(
    hands: Sequence[Hold],
    feet: Sequence[Hold],
    wall_angle_deg: float,
) -> float:
    if not hands or not feet:
        return 0.0

    min_hand_y = min(hold_point(hold)[1] for hold in hands)
    max_foot_y = max(hold_point(hold)[1] for hold in feet)
    gap = min_hand_y - max_foot_y
    if MIN_COMFORTABLE_HAND_FOOT_GAP_M <= gap <= MAX_COMFORTABLE_HAND_FOOT_GAP_M:
        return 0.0

    angle_factor = max(0.0, wall_angle_deg) / 45.0
    angle_factor *= ANGLE_COMPACT_STRETCHED_PENALTY_AT_45_DEG
    if gap < MIN_COMFORTABLE_HAND_FOOT_GAP_M:
        return angle_factor * (MIN_COMFORTABLE_HAND_FOOT_GAP_M - gap) / MIN_COMFORTABLE_HAND_FOOT_GAP_M

    return angle_factor * (gap - MAX_COMFORTABLE_HAND_FOOT_GAP_M) / MAX_COMFORTABLE_HAND_FOOT_GAP_M


def triangle_rule_penalty(hands: Sequence[Hold], feet: Sequence[Hold]) -> float:
    if not hands or not feet:
        return 1.0

    hand_points = [hold_point(hold) for hold in hands]
    foot_points = [hold_point(hold) for hold in feet]
    hand_center_x = sum(point[0] for point in hand_points) / len(hand_points)
    hand_min_x = min(point[0] for point in hand_points)
    hand_max_x = max(point[0] for point in hand_points)
    hand_span = max(0.3, hand_max_x - hand_min_x)

    penalty = 0.0
    for foot_x, _ in foot_points:
        if hand_min_x <= foot_x <= hand_max_x:
            continue
        penalty += abs(foot_x - hand_center_x) / hand_span
    return penalty / len(foot_points)


def hold_quality_penalty(holds: Sequence[Hold]) -> float:
    if not holds:
        return 1.0
    average_quality = sum(clamp_quality(hold.quality) for hold in holds) / len(holds)
    return (10.0 - average_quality) / 9.0


def clamp_quality(value: Optional[int]) -> int:
    if value is None:
        return 5
    return min(10, max(1, int(value)))


def force_alignment_penalty(
    holds: Sequence[Hold],
    center: Tuple[float, float],
) -> float:
    penalties = []
    for hold in holds:
        vectors = parse_force_vectors(hold.force_vectors)
        if not vectors:
            penalties.append(0.5)
            continue

        point = hold_point(hold)
        target = normalize((center[0] - point[0], center[1] - point[1]))
        if target is None:
            penalties.append(0.0)
            continue

        best_alignment = -1.0
        for vector in vectors:
            vector_direction = normalize((
                float(vector.get("dx", 0.0)),
                float(vector.get("dy", 0.0)),
            ))
            if vector_direction is None:
                continue
            best_alignment = max(best_alignment, dot(vector_direction, target))
        penalties.append((1.0 - max(best_alignment, -1.0)) / 2.0)

    return sum(penalties) / len(penalties) if penalties else 1.0


def parse_force_vectors(raw_vectors) -> List[dict]:
    if not raw_vectors:
        return []
    if isinstance(raw_vectors, list):
        return raw_vectors
    try:
        parsed = json.loads(raw_vectors)
    except (TypeError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def normalize(vector: Tuple[float, float]) -> Optional[Tuple[float, float]]:
    length = math.hypot(vector[0], vector[1])
    if length == 0:
        return None
    return (vector[0] / length, vector[1] / length)


def dot(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1]


def contact_count_penalty(contact_count: int) -> float:
    return (MAX_CONTACTS - contact_count) / (MAX_CONTACTS - 1)
