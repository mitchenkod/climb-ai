import os
import random
import numpy as np
import cv2
import sys
print(sys.path)

# domain models
from backend.models.gym import Gym
from backend.models.wall import Wall
from backend.models.surface import Surface
from backend.models.hold import Hold
from backend.models.hold_in_route import HoldInRoute

# routing
from backend.routing.generator import generate_route

# visualization
from backend.visualization.overlay import draw_route


# -----------------------
# helpers
# -----------------------

def ensure_sample_image(path="data/samples/wall.jpg"):
    os.makedirs("data/samples", exist_ok=True)

    if os.path.exists(path):
        return path

    # создаём пустое изображение стены
    img = np.ones((800, 600, 3), dtype=np.uint8) * 240
    cv2.putText(img, "DEV WALL", (180, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2, (0, 0, 0), 2)

    cv2.imwrite(path, img)
    return path


def generate_fake_holds(surface, n=15):
    holds = []
    for i in range(n):
        x = random.uniform(0.1, 0.9)
        y = random.uniform(0.1, 0.9)

        hold = Hold(
            id=i,
            x=x,
            y=y,
            surface=surface,
        )
        surface.holds.append(hold)
        holds.append(hold)

    for hold in holds:
        print(f"{hold.x}, {hold.y}")
    return holds


# -----------------------
# main pipeline
# -----------------------

def main():
    print("\n🚀 Starting DEV bootstrap pipeline\n")

    # 1. Gym
    gym = Gym(name="DevGym")

    # 2. Wall
    wall = Wall()
    gym.walls.append(wall)

    # 3. Surface
    surface = Surface(
        name="MainPlane",
        angle=-10,
        origin=(0, 0)
    )
    wall.add_plane(surface)

    # 4. Fake holds
    holds = generate_fake_holds(surface, n=18)

    print(f"Generated holds: {len(holds)}")

    # 5. Generate route
    route = generate_route(gym.all_holds())

    # 6. Image
    image_path = ensure_sample_image()

    # 7. Overlay
    output_path = "data/samples/output_route.jpg"
    draw_route(image_path, gym, route, output_path)

    print(f"\n✅ Overlay saved to: {output_path}\n")
    print("🎉 DEV pipeline completed successfully!\n")


if __name__ == "__main__":
    main()