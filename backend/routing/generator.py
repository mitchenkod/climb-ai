def generate_route(holds):
    """
    Генерация простого маршрута:
    - Нижние 4 зацепки = старт
    - Верхняя зацепка = топ
    - Остальные = промежуточные
    """
    if not holds:
        return []

    # сортируем по y (от нижней к верхней)
    holds_sorted = sorted(holds, key=lambda h: h.y, reverse=False)

    # стартовые
    start_holds = holds_sorted[:4]
    for h in start_holds:
        h.role = 'start'

    # топ/финиш
    finish_hold = holds_sorted[-1]
    finish_hold.role = 'finish'

    # остальные
    for h in holds_sorted[4:-1]:
        h.role = 'intermediate'

    # простой маршрут — отсортированные по высоте
    route = start_holds + holds_sorted[4:-1] + [finish_hold]
    return route

__all__ = ["generate_route"]
