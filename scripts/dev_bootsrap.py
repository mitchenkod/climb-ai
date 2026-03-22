import os
import random
import numpy as np
import cv2
import sys
from pathlib import Path

# Добавить корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# domain models
from backend.models.gym import Gym
from backend.models.wall import Wall
from backend.models.surface import Surface
from backend.models.hold import Hold
from backend.models.graph import Movement, BodyPosition, MovementHold
from backend.models.route import Route
from backend.models.movement_graph import MovementGraph
from backend.models.hold_in_route import HoldInRoute
from backend.db.database import get_session
from sqlmodel import select

# routing
from backend.services.climbing.route_builder import build_route_for_surface

# visualization
from backend.visualization.overlay import draw_route, draw_graph

# database
from backend.db.database import init_db

# graph building
from backend.services.climbing.graph_builder import create_movement_graph


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
        z = random.uniform(0.0, 0.5)

        hold = Hold(
            id=i,
            x=x,
            y=y,
            z=z,
            hold_type="crimp",  # Добавляем обязательный hold_type
            surface=surface,
        )
        surface.holds.append(hold)
        holds.append(hold)

    for hold in holds:
        print(f"{hold.x}, {hold.y}")
    return holds


def cleanup_test_data(session):
    """Удаляет все тестовые данные: зацепы, вершины и рёбра графа"""
    try:
        print("🧹 Cleaning up test data...\n")
        
        # Удаляем переходы BodyPosition
        edges = session.exec(select(BodyPosition)).all()
        for edge in edges:
            session.delete(edge)
        print(f"  Deleted {len(edges)} body positions")
        
        # Удаляем связи между движениями и зацепками
        movement_holds = session.exec(select(MovementHold)).all()
        for mh in movement_holds:
            session.delete(mh)
        print(f"  Deleted {len(movement_holds)} movement-hold associations")
        
        # Удаляем движения
        nodes = session.exec(select(Movement)).all()
        for node in nodes:
            session.delete(node)
        print(f"  Deleted {len(nodes)} movements")
        
        # Удаляем движения
        nodes = session.exec(select(BodyPosition)).all()
        for node in nodes:
            session.delete(node)
        print(f"  Deleted {len(nodes)} body positions")


        # Удаляем маршруты
        routes = session.exec(select(Route)).all()
        for r in routes:
            session.delete(r)
        print(f"  Deleted {len(routes)} routes")
        
        # Удаляем графы движений
        movement_graphs = session.exec(select(MovementGraph)).all()
        for mg in movement_graphs:
            session.delete(mg)
        print(f"  Deleted {len(movement_graphs)} movement graphs")
        
        # Удаляем зацепки
        holds = session.exec(select(Hold)).all()
        for hold in holds:
            session.delete(hold)
        print(f"  Deleted {len(holds)} holds\n")
        
        session.commit()
    except Exception as e:
        print(f"  Note: {e}\n")


# -----------------------
# main pipeline
# -----------------------

def main():
    print("\n🚀 Starting DEV bootstrap pipeline\n")
    
    # Удаляем старую БД и создаём новую со всеми таблицами
    db_path = "backend/app.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"🧹 Removed old database: {db_path}\n")
    
    init_db()
    print("✅ Database initialized with new schema\n")
    
    for session in get_session():
        # 0. Cleanup old test data
        cleanup_test_data(session)
        
        # 1. Gym
        gym = Gym(name="DevGym")
        session.add(gym)

        # 2. Wall
        wall = Wall()
        gym.walls.append(wall)

        # 3. Surface
        surface = Surface(
            angle=-10,
            width=600,
            height=800,
            origin_x=0,
            origin_y=0,
            origin_z=0,
            normal_x=0,
            normal_y=-0.1736,  # cos(10 degrees)
            normal_z=0.9848     # sin(10 degrees)
        )
        wall.add_plane(surface)

        # 4. Fake holds
        holds = generate_fake_holds(surface, n=18)

        print(f"Generated holds: {len(holds)}")

        # 5. Generate route
        result = build_route_for_surface(surface, session=session)
        route = result["route"]

        # 6. Image
        image_path = ensure_sample_image()

        # 7. Overlay
        output_route_path = "data/samples/output_route.jpg"
        draw_route(image_path, gym, route, output_route_path)
        print(f"\n✅ Route overlay saved to: {output_route_path}\n")

        # 8. Build and visualize movement graph
        graph, graph_nodes, hold_map = create_movement_graph(holds, max_contacts=4, distance_threshold=0.3)
        output_graph_path = "data/samples/output_graph.jpg"
        draw_graph(image_path, graph_nodes, hold_map, output_graph_path)
        print(f"✅ Graph overlay saved to: {output_graph_path}\n")
        
        print("🎉 DEV pipeline completed successfully!\n")
        break


if __name__ == "__main__":
    main()