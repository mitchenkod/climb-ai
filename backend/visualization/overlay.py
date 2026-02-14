import cv2

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
        if hold_in_route.role in ('start', 'finish'):
            color = (0, 255, 255)  # жёлтый (BGR)
        else:
            color = (0, 0, 255)    # красный

        x = int(hold_in_route.hold.x * image.shape[1])
        y = int(hold_in_route.hold.y * image.shape[0])
        cv2.circle(image, (x, y), 15, color, -1)  # заливка круга

    cv2.imwrite(output_path, image)
    return output_path