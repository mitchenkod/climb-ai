from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from backend.db import get_session
from backend.models.surface import Surface
from backend.services.climbing.route_builder import build_route_for_surface
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter()

@router.post("/routes")
def create_route(
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    # Получить первый surface
    statement = select(Surface).limit(1)
    surface = session.exec(statement).first()
    
    if not surface:
        raise HTTPException(status_code=404, detail="No surfaces found")
    
    # Запустить build_route_for_surface
    result = build_route_for_surface(surface, session=session)
    
    # Вернуть результат
    return {
        "route_id": result["route"].id,
        "movement_graph_id": result["movement_graph"].id,
        "start_position": result["start_position"].id if result["start_position"] else None,
        "start_holds": [{'x': h.x, 'y': h.y} for h in result["start_holds"]]
    }