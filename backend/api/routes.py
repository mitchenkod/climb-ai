from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from backend.db import get_session
from backend.models.surface import Surface
from backend.services.climbing.route_builder import build_route_for_surface
from pydantic import BaseModel
from typing import Dict, Any, Optional

router = APIRouter()

class RouteInput(BaseModel):
    wall_id: Optional[int] = None
    surface_id: Optional[int] = None
    name: str = "auto_route"

@router.post("/routes")
def create_route(
    data: RouteInput,
    session: Session = Depends(get_session)
) -> Dict[str, Any]:
    if data.surface_id is not None:
        surface = session.get(Surface, data.surface_id)
    elif data.wall_id is not None:
        statement = select(Surface).where(Surface.wall_id == data.wall_id).limit(1)
        surface = session.exec(statement).first()
    else:
        raise HTTPException(status_code=400, detail="wall_id or surface_id is required")
    
    if not surface:
        raise HTTPException(status_code=404, detail="Surface not found")
    
    result = build_route_for_surface(surface, session=session, route_name=data.name)
    
    return {
        "route_id": result["route"].id,
        "movement_graph_id": result["movement_graph"].id,
        "start_position": result["start_position"].id if result["start_position"] else None,
        "start_holds": [{'id': h.id, 'x': h.x, 'y': h.y} for h in result["start_holds"]]
    }
