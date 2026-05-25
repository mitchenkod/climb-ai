import unittest

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

import backend.db.database as database
from backend.api.gym import GymInput, save_gym
from backend.api.wall import (
    HoldsInput,
    SurfaceGeometryInput,
    WallInput,
    add_holds,
    get_wall,
    save_wall,
    update_surface_geometry,
)
from backend.geometry.normalization import (
    SurfaceGeometry,
    normalized_to_pixel_coords,
    pixel_to_surface_coords,
)


class WallGeometryTest(unittest.TestCase):
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

    def create_wall(self, width_m=3.0, height_m=4.0, image_width_px=300, image_height_px=400):
        save_gym(GymInput(name="Test Gym"), self.session)
        return save_wall(
            WallInput(
                gym_id=1,
                image_name="wall.jpg",
                width_m=width_m,
                height_m=height_m,
                image_width_px=image_width_px,
                image_height_px=image_height_px,
                angle=15.0,
            ),
            self.session,
        )

    def test_pixel_to_surface_coords_converts_image_pixels_to_meters(self):
        geometry = SurfaceGeometry(
            width_m=3.0,
            height_m=4.0,
            image_width_px=300,
            image_height_px=400,
            angle_deg=15.0,
        )

        x_m, y_m = pixel_to_surface_coords(150, 100, geometry)

        self.assertEqual(x_m, 1.5)
        self.assertEqual(y_m, 3.0)

    def test_normalized_to_pixel_coords_converts_normalized_ui_coords(self):
        geometry = SurfaceGeometry(
            width_m=3.0,
            height_m=4.0,
            image_width_px=300,
            image_height_px=400,
        )

        x_px, y_px = normalized_to_pixel_coords(0.5, 0.25, geometry)

        self.assertEqual(x_px, 150)
        self.assertEqual(y_px, 100)

    def test_wall_creation_creates_default_surface_with_geometry(self):
        result = self.create_wall()

        wall = get_wall(result["wall_id"], self.session)
        surface = wall["surfaces"][0]

        self.assertEqual(result["surface_id"], surface.id)
        self.assertEqual(surface.width_m, 3.0)
        self.assertEqual(surface.height_m, 4.0)
        self.assertEqual(surface.image_width_px, 300)
        self.assertEqual(surface.image_height_px, 400)
        self.assertEqual(surface.angle, 15.0)

    def test_add_hold_with_pixel_coords_stores_normalized_pixel_and_meter_coords(self):
        self.create_wall()

        result = add_holds(
            1,
            HoldsInput(holds=[{"x_px": 150, "y_px": 100, "hold_type": "jug"}]),
            self.session,
        )
        hold = result["holds"][0]

        self.assertEqual(hold.x, 0.5)
        self.assertEqual(hold.y, 0.25)
        self.assertEqual(hold.x_px, 150)
        self.assertEqual(hold.y_px, 100)
        self.assertEqual(hold.x_m, 1.5)
        self.assertEqual(hold.y_m, 3.0)

    def test_add_hold_with_normalized_coords_derives_pixel_and_meter_coords(self):
        self.create_wall()

        result = add_holds(
            1,
            HoldsInput(holds=[{"x": 0.5, "y": 0.25, "hold_type": "crimp"}]),
            self.session,
        )
        hold = result["holds"][0]

        self.assertEqual(hold.x, 0.5)
        self.assertEqual(hold.y, 0.25)
        self.assertEqual(hold.x_px, 150)
        self.assertEqual(hold.y_px, 100)
        self.assertEqual(hold.x_m, 1.5)
        self.assertEqual(hold.y_m, 3.0)

    def test_update_surface_geometry_recalculates_existing_holds(self):
        self.create_wall()
        add_holds(
            1,
            HoldsInput(holds=[{"x_px": 150, "y_px": 100, "hold_type": "jug"}]),
            self.session,
        )

        result = update_surface_geometry(
            1,
            SurfaceGeometryInput(
                width_m=6.0,
                height_m=8.0,
                image_width_px=300,
                image_height_px=400,
                angle=20.0,
            ),
            self.session,
        )
        surface = result["surface"]
        hold = result["holds"][0]

        self.assertEqual(surface.width_m, 6.0)
        self.assertEqual(surface.height_m, 8.0)
        self.assertEqual(surface.angle, 20.0)
        self.assertEqual(hold.x, 0.5)
        self.assertEqual(hold.y, 0.25)
        self.assertEqual(hold.x_px, 150)
        self.assertEqual(hold.y_px, 100)
        self.assertEqual(hold.x_m, 3.0)
        self.assertEqual(hold.y_m, 6.0)


if __name__ == "__main__":
    unittest.main()
