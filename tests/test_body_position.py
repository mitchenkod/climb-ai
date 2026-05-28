import json
import random
import unittest

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

import backend.db.database as database
from backend.models.hold import Hold
from backend.models.surface import Surface
from backend.services.climbing.body_position import (
    score_body_position,
    select_best_body_position,
    split_hands_and_feet,
)
from backend.services.climbing.route_builder import build_route_for_surface


def make_hold(
    x_m,
    y_m,
    quality=8,
    vectors=None,
    hold_id=None,
    hold_type="jug",
):
    return Hold(
        id=hold_id,
        x=x_m,
        y=1.0 - y_m,
        z=0.0,
        x_m=x_m,
        y_m=y_m,
        hold_type=hold_type,
        quality=quality,
        force_vectors=json.dumps(vectors or []),
    )


class BodyPositionTest(unittest.TestCase):
    def test_scores_balanced_four_hold_position_as_realistic(self):
        holds = [
            make_hold(1.0, 0.5, vectors=[{"dx": 1, "dy": 1}]),
            make_hold(1.8, 0.5, vectors=[{"dx": -1, "dy": 1}]),
            make_hold(1.0, 1.55, vectors=[{"dx": 1, "dy": -1}]),
            make_hold(1.8, 1.55, vectors=[{"dx": -1, "dy": -1}]),
        ]

        score = score_body_position(holds)

        self.assertTrue(score.is_realistic)
        self.assertLess(score.score, 2.0)
        self.assertEqual(set(score.breakdown), {
            "average_center_distance",
            "max_center_distance",
            "hand_foot_distance",
            "angle_compact_stretched",
            "triangle_rule",
            "hold_quality",
            "force_alignment",
            "contact_count",
        })

    def test_rejects_positions_with_holds_too_far_apart(self):
        holds = [
            make_hold(0.0, 0.2),
            make_hold(4.0, 0.2),
            make_hold(0.0, 3.2),
            make_hold(4.0, 3.2),
        ]

        score = score_body_position(holds)

        self.assertFalse(score.is_realistic)
        self.assertGreater(score.score, 4.0)

    def test_rejects_start_with_hands_too_high_above_feets(self):
        holds = [
            make_hold(0.5, 0.8),
            make_hold(1.3, 1.0),
            make_hold(0.5, 2.3),
            make_hold(1.3, 2.3),
        ]

        score = score_body_position(holds)

        self.assertFalse(score.is_realistic)
        self.assertEqual(score.breakdown, {"start_hands_too_high": 1.0})

    def test_rejects_start_when_hand_is_too_far_from_nearest_foot(self):
        holds = [
            make_hold(0.5, 0.5),
            make_hold(1.2, 0.5),
            make_hold(0.4, 1.5),
            make_hold(2.8, 1.5),
        ]

        score = score_body_position(holds)

        self.assertFalse(score.is_realistic)
        self.assertEqual(score.breakdown, {"start_hand_reach_too_far": 1.0})

    def test_hold_quality_increases_position_difficulty(self):
        high_quality = [
            make_hold(1.0, 0.5, quality=9),
            make_hold(1.8, 0.5, quality=9),
            make_hold(1.0, 1.55, quality=9),
            make_hold(1.8, 1.55, quality=9),
        ]
        low_quality = [
            make_hold(1.0, 0.5, quality=2),
            make_hold(1.8, 0.5, quality=2),
            make_hold(1.0, 1.55, quality=2),
            make_hold(1.8, 1.55, quality=2),
        ]

        self.assertGreater(
            score_body_position(low_quality).score,
            score_body_position(high_quality).score,
        )

    def test_overhang_increases_penalty_for_too_compact_positions(self):
        compact = [
            make_hold(1.0, 1.0),
            make_hold(1.8, 1.0),
            make_hold(1.0, 1.5),
            make_hold(1.8, 1.5),
        ]

        vertical = score_body_position(compact, wall_angle_deg=0.0)
        overhang = score_body_position(compact, wall_angle_deg=40.0)

        self.assertEqual(vertical.breakdown["angle_compact_stretched"], 0.0)
        self.assertGreater(overhang.breakdown["angle_compact_stretched"], 0.0)
        self.assertGreater(overhang.score, vertical.score)

    def test_force_vectors_are_compared_to_direction_to_position_center(self):
        good_alignment = [
            make_hold(1.0, 1.0, vectors=[{"dx": 1, "dy": 0}]),
            make_hold(2.0, 1.0, vectors=[{"dx": -1, "dy": 0}]),
        ]
        bad_alignment = [
            make_hold(1.0, 1.0, vectors=[{"dx": -1, "dy": 0}]),
            make_hold(2.0, 1.0, vectors=[{"dx": 1, "dy": 0}]),
        ]

        self.assertGreater(
            score_body_position(bad_alignment).breakdown["force_alignment"],
            score_body_position(good_alignment).breakdown["force_alignment"],
        )

    def test_select_best_body_position_prefers_realistic_cluster(self):
        bad_far_holds = [
            make_hold(0.0, 0.1, hold_id=1),
            make_hold(4.0, 0.1, hold_id=2),
            make_hold(0.0, 3.5, hold_id=3),
            make_hold(4.0, 3.5, hold_id=4),
        ]
        good_holds = [
            make_hold(1.0, 0.5, hold_id=5),
            make_hold(1.8, 0.5, hold_id=6),
            make_hold(1.0, 1.55, hold_id=7),
            make_hold(1.8, 1.55, hold_id=8),
        ]

        score = select_best_body_position(bad_far_holds + good_holds)

        self.assertTrue(score.is_realistic)
        self.assertEqual({hold.id for hold in score.holds}, {5, 6, 7, 8})

    def test_foot_holds_are_not_valid_for_start_hands(self):
        holds = [
            make_hold(1.0, 0.5),
            make_hold(1.8, 0.5),
            make_hold(1.0, 1.7, hold_type="foot"),
            make_hold(1.8, 1.7),
        ]

        score = score_body_position(holds)

        self.assertFalse(score.is_realistic)
        self.assertEqual(score.breakdown, {"foot_hold_used_by_hand": 1.0})

    def test_foot_holds_are_allowed_for_start_feet(self):
        holds = [
            make_hold(1.0, 0.5, hold_type="foot"),
            make_hold(1.8, 0.5, hold_type="foot"),
            make_hold(1.0, 1.55),
            make_hold(1.8, 1.55),
        ]

        score = score_body_position(holds)

        self.assertTrue(score.is_realistic)

    def test_select_best_body_position_does_not_place_foot_hold_in_hands(self):
        hand_foot_hold = make_hold(1.0, 1.7, hold_id=1, hold_type="foot")
        foot_foot_hold = make_hold(1.0, 0.5, hold_id=2, hold_type="foot")
        regular_holds = [
            make_hold(1.8, 0.5, hold_id=3),
            make_hold(1.0, 1.55, hold_id=4),
            make_hold(1.8, 1.55, hold_id=5),
        ]

        score = select_best_body_position([hand_foot_hold, foot_foot_hold] + regular_holds)
        hands, _feet = split_hands_and_feet(score.holds)

        self.assertTrue(score.is_realistic)
        self.assertNotIn(1, {hold.id for hold in hands})

    def test_start_feet_cannot_be_more_than_half_meter_above_lowest_wall_hold(self):
        wall_holds = [
            make_hold(0.5, 0.0, hold_id=1),
            make_hold(1.0, 0.6, hold_id=2),
            make_hold(1.8, 0.6, hold_id=3),
            make_hold(1.0, 1.7, hold_id=4),
            make_hold(1.8, 1.7, hold_id=5),
        ]

        score = score_body_position(
            wall_holds[1:],
            lowest_hold_y_m=0.0,
            wall_angle_deg=0.0,
        )

        self.assertFalse(score.is_realistic)
        self.assertEqual(score.breakdown, {"start_feet_too_high": 1.0})

    def test_start_foot_height_limit_uses_wall_angle_vertical_projection(self):
        wall_holds = [
            make_hold(0.5, 0.0, hold_id=1),
            make_hold(1.0, 0.6, hold_id=2),
            make_hold(1.8, 0.6, hold_id=3),
            make_hold(1.0, 1.7, hold_id=4),
            make_hold(1.8, 1.7, hold_id=5),
        ]

        score = score_body_position(
            wall_holds[1:],
            lowest_hold_y_m=0.0,
            wall_angle_deg=45.0,
        )

        self.assertTrue(score.is_realistic)

    def test_select_best_body_position_uses_lowest_hold_on_wall_for_start_feet(self):
        low_reference = make_hold(0.5, 0.0, hold_id=1)
        too_high_feet = [
            make_hold(1.0, 0.6, hold_id=2),
            make_hold(1.8, 0.6, hold_id=3),
            make_hold(1.0, 1.7, hold_id=4),
            make_hold(1.8, 1.7, hold_id=5),
        ]
        valid_start = [
            make_hold(1.0, 0.2, hold_id=6),
            make_hold(1.8, 0.2, hold_id=7),
            make_hold(1.0, 1.25, hold_id=8),
            make_hold(1.8, 1.25, hold_id=9),
        ]

        score = select_best_body_position([low_reference] + too_high_feet + valid_start)

        self.assertTrue(score.is_realistic)
        self.assertTrue({6, 7}.issubset({hold.id for hold in score.holds}))

    def test_select_best_body_position_prefers_four_contact_start_when_available(self):
        holds = [
            make_hold(1.0, 0.5, hold_id=1),
            make_hold(1.8, 0.5, hold_id=2),
            make_hold(1.0, 1.55, hold_id=3),
            make_hold(1.8, 1.55, hold_id=4),
            make_hold(1.4, 1.0, hold_id=5, quality=10),
        ]

        score = select_best_body_position(holds)

        self.assertTrue(score.is_realistic)
        self.assertEqual(len(score.holds), 4)

    def test_randomized_selection_can_choose_different_good_starts(self):
        holds = [
            make_hold(0.9, 0.2, hold_id=1),
            make_hold(1.7, 0.2, hold_id=2),
            make_hold(0.9, 1.25, hold_id=3),
            make_hold(1.7, 1.25, hold_id=4),
            make_hold(1.2, 0.25, hold_id=5),
            make_hold(2.0, 0.25, hold_id=6),
            make_hold(1.2, 1.3, hold_id=7),
            make_hold(2.0, 1.3, hold_id=8),
        ]

        selected = {
            tuple(sorted(hold.id for hold in select_best_body_position(
                holds,
                randomize=True,
                rng=random.Random(seed),
            ).holds))
            for seed in range(20)
        }

        self.assertGreater(len(selected), 1)

    def test_selection_skips_excluded_start_when_alternative_exists(self):
        holds = [
            make_hold(0.9, 0.2, hold_id=1),
            make_hold(1.7, 0.2, hold_id=2),
            make_hold(0.9, 1.25, hold_id=3),
            make_hold(1.7, 1.25, hold_id=4),
            make_hold(1.2, 0.25, hold_id=5),
            make_hold(2.0, 0.25, hold_id=6),
            make_hold(1.2, 1.3, hold_id=7),
            make_hold(2.0, 1.3, hold_id=8),
        ]

        first = select_best_body_position(holds)
        excluded_signature = tuple(sorted(hold.id for hold in first.holds))

        second = select_best_body_position(
            holds,
            excluded_signatures={excluded_signature},
        )

        self.assertNotEqual(
            excluded_signature,
            tuple(sorted(hold.id for hold in second.holds)),
        )


class RouteBuilderBodyPositionTest(unittest.TestCase):
    def setUp(self):
        self.original_engine = database.engine
        database.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        database.init_db()
        self.session = Session(database.engine)

    def tearDown(self):
        self.session.close()
        database.engine = self.original_engine

    def test_route_builder_stores_start_position_cost_and_route_difficulty(self):
        surface = Surface(
            wall_id=1,
            angle=0.0,
            width=3.0,
            height=4.0,
            width_m=3.0,
            height_m=4.0,
            image_width_px=300,
            image_height_px=400,
            origin_x=0.0,
            origin_y=0.0,
            origin_z=0.0,
            normal_x=0.0,
            normal_y=0.0,
            normal_z=1.0,
        )
        self.session.add(surface)
        self.session.commit()
        self.session.refresh(surface)

        for hold in [
            make_hold(1.0, 0.5),
            make_hold(1.8, 0.5),
            make_hold(1.0, 1.55),
            make_hold(1.8, 1.55),
        ]:
            hold.surface_id = surface.id
            self.session.add(hold)
        self.session.commit()
        self.session.refresh(surface)

        result = build_route_for_surface(surface, session=self.session)

        self.assertIsNotNone(result["start_score"])
        self.assertAlmostEqual(
            result["route"].difficulty_score,
            result["start_position"].cost,
        )
        self.assertEqual(len(result["start_holds"]), 4)

    def test_route_builder_avoids_existing_start_signature_when_possible(self):
        surface = Surface(
            wall_id=1,
            angle=0.0,
            width=3.0,
            height=4.0,
            width_m=3.0,
            height_m=4.0,
            image_width_px=300,
            image_height_px=400,
            origin_x=0.0,
            origin_y=0.0,
            origin_z=0.0,
            normal_x=0.0,
            normal_y=0.0,
            normal_z=1.0,
        )
        self.session.add(surface)
        self.session.commit()
        self.session.refresh(surface)

        for hold in [
            make_hold(0.9, 0.2),
            make_hold(1.7, 0.2),
            make_hold(0.9, 1.25),
            make_hold(1.7, 1.25),
            make_hold(1.2, 0.25),
            make_hold(2.0, 0.25),
            make_hold(1.2, 1.3),
            make_hold(2.0, 1.3),
        ]:
            hold.surface_id = surface.id
            self.session.add(hold)
        self.session.commit()
        self.session.refresh(surface)

        first = build_route_for_surface(surface, session=self.session)
        second = build_route_for_surface(surface, session=self.session)
        first_signature = tuple(sorted(hold.id for hold in first["start_holds"]))
        second_signature = tuple(sorted(hold.id for hold in second["start_holds"]))

        self.assertNotEqual(first_signature, second_signature)


if __name__ == "__main__":
    unittest.main()
