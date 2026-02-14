from backend.models.route import Route
from backend.models.hold_in_route import HoldInRoute

def generate_route(holds):
    """
    Генерация простого маршрута:
    - Нижние 4 зацепки = старт
    - Верхняя зацепка = топ
    - Остальные = промежуточные
    """
    if not holds:
        return []
    route = Route()

    # сортируем по y (от нижней к верхней)
    holds_sorted = sorted(holds, key=lambda h: h.y, reverse=False)

    # стартовые
    start_holds = holds_sorted[:4]
    for h in start_holds:
        HoldInRoute(route=route, hold=h, role='start')

    # топ/финиш
    finish_hold = holds_sorted[-1]
    HoldInRoute(route=route, hold=finish_hold, role='finish')
 
    # остальные
    for h in holds_sorted[4:-1]:
        HoldInRoute(route=route, hold=finish_hold, role='intermediate')
    return route

__all__ = ["generate_route"]
