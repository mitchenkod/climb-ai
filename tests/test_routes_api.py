import unittest

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

import backend.db.database as database
import backend.api.routes as routes_api
from backend.api.gym import GymInput, save_gym
from backend.api.routes import (
    RouteInput,
    add_next_move,
    create_route,
    delete_wall_route,
    list_wall_routes,
)
from backend.api.wall import HoldsInput, WallInput, add_holds, save_wall
from backend.models.hold_in_route import HoldInRoute, HoldRole
from backend.models.movement_graph import MovementGraph
from backend.models.route import Route


class RoutesApiTest(unittest.TestCase):
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

    def create_wall_with_holds(self):
        save_gym(GymInput(name="Routes Gym"), self.session)
        wall = save_wall(
            WallInput(
                gym_id=1,
                image_name="wall.jpg",
                width_m=3.0,
                height_m=4.0,
                image_width_px=300,
                image_height_px=400,
                angle=0.0,
            ),
            self.session,
        )
        add_holds(
            wall["wall_id"],
            HoldsInput(
                holds=[
                    {"x_px": 90, "y_px": 380, "hold_type": "jug", "quality": 8},
                    {"x_px": 170, "y_px": 380, "hold_type": "jug", "quality": 8},
                    {"x_px": 90, "y_px": 275, "hold_type": "jug", "quality": 8},
                    {"x_px": 170, "y_px": 275, "hold_type": "jug", "quality": 8},
                    {"x_px": 120, "y_px": 375, "hold_type": "jug", "quality": 8},
                    {"x_px": 200, "y_px": 375, "hold_type": "jug", "quality": 8},
                    {"x_px": 120, "y_px": 270, "hold_type": "jug", "quality": 8},
                    {"x_px": 200, "y_px": 270, "hold_type": "jug", "quality": 8},
                ]
            ),
            self.session,
        )
        return wall["wall_id"]

    def test_list_wall_routes_returns_paginated_routes_with_start_holds(self):
        wall_id = self.create_wall_with_holds()
        first = create_route(RouteInput(wall_id=wall_id), self.session)
        second = create_route(RouteInput(wall_id=wall_id), self.session)

        result = list_wall_routes(wall_id, page=1, page_size=1, session=self.session)

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["page"], 1)
        self.assertEqual(len(result["routes"]), 1)
        self.assertEqual(result["routes"][0]["route_id"], second["route_id"])
        self.assertEqual(len(result["routes"][0]["start_holds"]), 4)
        self.assertIn("x_px", result["routes"][0]["start_holds"][0])
        self.assertNotEqual(first["route_id"], second["route_id"])

    def test_delete_wall_route_removes_route_links_and_movement_graph(self):
        wall_id = self.create_wall_with_holds()
        route = create_route(RouteInput(wall_id=wall_id), self.session)
        route_id = route["route_id"]

        result = delete_wall_route(wall_id, route_id, self.session)

        self.assertEqual(result, {"status": "deleted"})
        self.assertIsNone(self.session.get(Route, route_id))
        self.assertEqual(
            self.session.exec(
                select(HoldInRoute).where(HoldInRoute.route_id == route_id)
            ).all(),
            [],
        )
        self.assertEqual(
            self.session.exec(
                select(MovementGraph).where(MovementGraph.route_id == route_id)
            ).all(),
            [],
        )

    def test_add_next_move_appends_hold_and_returns_position_score(self):
        wall_id = self.create_wall_with_holds()
        route = create_route(RouteInput(wall_id=wall_id), self.session)
        add_holds(
            wall_id,
            HoldsInput(
                holds=[
                    {"x_px": 130, "y_px": 250, "hold_type": "jug", "quality": 8},
                    {"x_px": 150, "y_px": 50, "hold_type": "jug", "quality": 8},
                ]
            ),
            self.session,
        )
        previous_route_hold_ids = {
            item["hold"]["id"]
            for item in list_wall_routes(wall_id, page=1, page_size=1, session=self.session)["routes"][0]["holds"]
        }

        result = add_next_move(wall_id, route["route_id"], self.session)

        self.assertEqual(result["role"], "intermediate")
        self.assertIn("score", result["next_position"])
        self.assertEqual(len(result["next_position"]["hands"]), 2)
        self.assertEqual(len(result["next_position"]["feet"]), 2)
        self.assertTrue({
            hold["id"]
            for hold in result["next_position"]["feet"]
        }.issubset(previous_route_hold_ids))
        self.assertGreater(len(result["route"]["holds"]), len(route["start_holds"]))
        self.assertIn(result["new_hold"]["id"], [
            item["hold"]["id"]
            for item in result["route"]["holds"]
            if item["role"] == "intermediate"
        ])

    def test_add_next_move_can_probabilistically_attach_new_foot_after_initial_candidates(self):
        original_probability = routes_api.ATTACH_FOOT_PROBABILITY
        original_start_index = routes_api.ATTACH_FOOT_FROM_CANDIDATE_INDEX
        original_random = routes_api.random.random
        routes_api.ATTACH_FOOT_PROBABILITY = 1.0
        routes_api.ATTACH_FOOT_FROM_CANDIDATE_INDEX = 0
        routes_api.random.random = lambda: 0.0
        try:
            wall_id = self.create_wall_with_holds()
            route = create_route(RouteInput(wall_id=wall_id), self.session)
            add_holds(
                wall_id,
                HoldsInput(
                    holds=[
                        {"x_px": 135, "y_px": 250, "hold_type": "jug", "quality": 8},
                        {"x_px": 140, "y_px": 320, "hold_type": "foot", "quality": 2},
                        {"x_px": 150, "y_px": 50, "hold_type": "jug", "quality": 8},
                    ]
                ),
                self.session,
            )

            result = add_next_move(wall_id, route["route_id"], self.session)

            if result["attached_foot"] is not None:
                self.assertIn(result["attached_foot"]["id"], [
                    item["hold"]["id"]
                    for item in result["route"]["holds"]
                    if item["role"] == "foot_suggested"
                ])
        finally:
            routes_api.ATTACH_FOOT_PROBABILITY = original_probability
            routes_api.ATTACH_FOOT_FROM_CANDIDATE_INDEX = original_start_index
            routes_api.random.random = original_random

    def test_add_next_move_is_blocked_after_finish_hold(self):
        wall_id = self.create_wall_with_holds()
        route = create_route(RouteInput(wall_id=wall_id), self.session)
        self.session.add(
            HoldInRoute(
                route_id=route["route_id"],
                hold_id=route["start_holds"][0]["id"],
                role=HoldRole.FINISH,
                order_index=10,
            )
        )
        self.session.commit()

        with self.assertRaises(Exception) as context:
            add_next_move(wall_id, route["route_id"], self.session)

        self.assertEqual(context.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
