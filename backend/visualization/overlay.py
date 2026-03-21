import cv2
import colorsys
from typing import List


def generate_distinct_colors(n: int) -> List[tuple]:
    """
    Генерирует n уникальных цветов в формате BGR для OpenCV.
    Использует HSV для равномерного распределения цветов.
    """
    colors = []
    for i in range(n):
        hue = i / n  # Равномерное распределение по оттенку
        rgb = colorsys.hsv_to_rgb(hue, 0.8, 0.9)
        # Конвертируем RGB в BGR для OpenCV и масштабируем до 0-255
        bgr = (int(rgb[2] * 255), int(rgb[1] * 255), int(rgb[0] * 255))
        colors.append(bgr)
    return colors

def draw_route(image_path, gym, route, output_path="output_route.jpg"):
    """
    Рисует зацепки на изображении:
    - start/finish = жёлтый
    - intermediate = красный
    """
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")


    for hold in gym.all_holds():
        x = int(hold.x * image.shape[1])
        y = int(hold.y * image.shape[0])
        cv2.circle(image, (x, y), 5, (255, 0, 0), -1)  # заливка круга

    for hold_in_route in route.holds_in_route:
        print(f"{hold_in_route.role} {hold_in_route.hold.x} {hold_in_route.hold.y}\n")
        if hold_in_route.role in ('start', 'finish'):
            color = (0, 255, 255)  # жёлтый (BGR)
        else:
            color = (0, 0, 255)    # красный

        x = int(hold_in_route.hold.x * image.shape[1])
        y = int(hold_in_route.hold.y * image.shape[0])
        cv2.circle(image, (x, y), 15, color, 1)

    cv2.imwrite(output_path, image)
    return output_path


def draw_graph(image_path, graph_nodes, hold_map, output_path="output_graph.jpg"):
    """
    Рисует вершины графа на изображении.
    Для каждой вершины берёт все зацепы и обводит их кружком диаметром 2 уникального цвета.
    Рядом с каждой зацепкой пишет ID нодов, к которым она принадлежит.
    
    Args:
        image_path: путь к исходному изображению
        graph_nodes: список GraphNode объектов из графа
        hold_map: словарь {hold_id: Hold object} для получения координат
        output_path: путь сохранения результата
    """
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Генерируем уникальные цвета для каждой вершины
    colors = generate_distinct_colors(len(graph_nodes))
    
    # Создаём маппинг: hold_id -> список индексов нодов, которым принадлежит этот hold
    hold_to_nodes = {}
    for node_idx, node in enumerate(graph_nodes):
        hold_ids = [int(x) for x in node.signature.split(",")]
        for hold_id in hold_ids:
            if hold_id not in hold_to_nodes:
                hold_to_nodes[hold_id] = []
            hold_to_nodes[hold_id].append(node_idx)
    
    # Рисуем каждую вершину графа
    for node_idx, node in enumerate(graph_nodes):
        color = colors[node_idx]
        
        # Получаем все зацепы для этой вершины через signature
        # signature содержит ID зацепов через запятую
        hold_ids = [int(x) for x in node.signature.split(",")]
        
        # Обводим каждый зацеп из этой вершины кружком
        for hold_id in hold_ids:
            if hold_id in hold_map:
                hold = hold_map[hold_id]
                x = int(hold.x * image.shape[1])
                y = int(hold.y * image.shape[0])
                # Рисуем кружок диаметром 2 (радиус 1) с контуром
                cv2.circle(image, (x, y), 7, color, 1)
    
    # Добавляем текст с ID нодов рядом с каждой зацепкой
    for hold_id, node_indices in hold_to_nodes.items():
        if hold_id in hold_map:
            hold = hold_map[hold_id]
            x = int(hold.x * image.shape[1])
            y = int(hold.y * image.shape[0])
            
            # Форматируем текст: ID нодов через запятую
            nodes_text = ",".join(str(idx) for idx in sorted(node_indices))
            
            # Выводим текст рядом с зацепкой (смещение на 15 пиксель вправо и вверх)
            cv2.putText(image, nodes_text, (x + 10, y - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    
    cv2.imwrite(output_path, image)
    return output_path