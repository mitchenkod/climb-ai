import base64
from io import BytesIO
import tempfile
import unittest

from PIL import Image
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

import backend.db.database as database
import backend.api.wall as wall_api
from backend.api.gym import GymInput, save_gym
from backend.models.route import Route
from backend.api.wall import (
    HoldUpdateInput,
    HoldsInput,
    SurfaceGeometryInput,
    WallImageUploadInput,
    WallInput,
    add_holds,
    get_wall,
    save_wall,
    upload_wall_image,
    update_hold,
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
        self.original_image_dir = wall_api.IMAGE_DIR
        self.tmpdir = tempfile.TemporaryDirectory()
        wall_api.IMAGE_DIR = wall_api.Path(self.tmpdir.name)

    def tearDown(self):
        self.session.close()
        wall_api.IMAGE_DIR = self.original_image_dir
        self.tmpdir.cleanup()
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
            HoldsInput(
                holds=[
                    {
                        "x_px": 150,
                        "y_px": 100,
                        "hold_type": "jug",
                        "quality": 8,
                        "force_vectors": [{"name": "down", "dx": 0, "dy": -1}],
                    }
                ]
            ),
            self.session,
        )
        hold = result["holds"][0]

        self.assertEqual(hold.x, 0.5)
        self.assertEqual(hold.y, 0.25)
        self.assertEqual(hold.x_px, 150)
        self.assertEqual(hold.y_px, 100)
        self.assertEqual(hold.x_m, 1.5)
        self.assertEqual(hold.y_m, 3.0)
        self.assertEqual(hold.quality, 8)
        self.assertEqual(hold.force_vectors, '[{"name": "down", "dx": 0, "dy": -1}]')

    def test_upload_wall_image_saves_image_and_uses_actual_image_dimensions(self):
        save_gym(GymInput(name="Upload Gym"), self.session)
        buffer = BytesIO()
        Image.new("RGB", (1, 1), color="white").save(buffer, format="PNG")
        png_1x1 = base64.b64encode(buffer.getvalue()).decode("ascii")

        result = upload_wall_image(
            WallImageUploadInput(
                gym_id=1,
                image_name="wall.png",
                image_data=f"data:image/png;base64,{png_1x1}",
                width_m=3.0,
                height_m=4.0,
                angle=10.0,
            ),
            self.session,
        )
        wall = get_wall(result["wall_id"], self.session)
        surface = wall["surfaces"][0]

        self.assertTrue((wall_api.IMAGE_DIR / wall["image_name"]).exists())
        self.assertEqual(surface.image_width_px, 1)
        self.assertEqual(surface.image_height_px, 1)
        self.assertEqual(surface.width_m, 3.0)
        self.assertEqual(surface.height_m, 4.0)
        self.assertEqual(surface.angle, 10.0)

    def test_work_area_projection_normalizes_hold_coordinates(self):
        save_gym(GymInput(name="Projection Gym"), self.session)
        buffer = BytesIO()
        Image.new("RGB", (100, 100), color="white").save(buffer, format="PNG")
        png = base64.b64encode(buffer.getvalue()).decode("ascii")

        result = upload_wall_image(
            WallImageUploadInput(
                gym_id=1,
                image_name="wall.png",
                image_data=f"data:image/png;base64,{png}",
                width_m=4.0,
                height_m=4.0,
                angle=0.0,
                work_area=[
                    {"x": 10, "y": 10},
                    {"x": 90, "y": 10},
                    {"x": 90, "y": 90},
                    {"x": 10, "y": 90},
                ],
            ),
            self.session,
        )

        hold_result = add_holds(
            result["wall_id"],
            HoldsInput(holds=[{"x_px": 50, "y_px": 50, "hold_type": "jug"}]),
            self.session,
        )
        hold = hold_result["holds"][0]

        self.assertAlmostEqual(hold.x, 0.5)
        self.assertAlmostEqual(hold.y, 0.5)
        self.assertAlmostEqual(hold.x_m, 2.0)
        self.assertAlmostEqual(hold.y_m, 2.0)

    def test_update_hold_updates_geometry_metadata_and_force_vectors(self):
        self.create_wall()
        add_holds(
            1,
            HoldsInput(holds=[{"x_px": 150, "y_px": 100, "hold_type": "jug"}]),
            self.session,
        )

        hold = update_hold(
            1,
            HoldUpdateInput(
                x_px=30,
                y_px=40,
                hold_type="sidepull",
                quality=9,
                force_vectors=[{"name": "left", "dx": -1, "dy": 0}],
            ),
            self.session,
        )

        self.assertEqual(hold.x, 0.1)
        self.assertEqual(hold.y, 0.1)
        self.assertEqual(hold.x_px, 30)
        self.assertEqual(hold.y_px, 40)
        self.assertEqual(hold.x_m, 0.3)
        self.assertEqual(hold.y_m, 3.6)
        self.assertEqual(hold.hold_type, "sidepull")
        self.assertEqual(hold.quality, 9)
        self.assertEqual(hold.force_vectors, '[{"name": "left", "dx": -1, "dy": 0}]')

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

    def test_update_surface_geometry_is_blocked_after_route_creation(self):
        self.create_wall()
        self.session.add(Route(name="existing route", wall_id=1))
        self.session.commit()

        with self.assertRaises(wall_api.HTTPException) as context:
            update_surface_geometry(
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

        self.assertEqual(context.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
