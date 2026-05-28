from fastapi import FastAPI
from fastapi.responses import FileResponse
from backend.db.database import init_db
from backend.api.gym import router as gym_router
from backend.api.wall import router as wall_router
from backend.api.routes import router as routes_router
from fastapi.staticfiles import StaticFiles

app = FastAPI()
@app.on_event("startup")
def on_startup():
    print("START BACKEND")
    init_db()
app.include_router(gym_router, prefix='/api')
app.include_router(wall_router, prefix='/api')
app.include_router(routes_router, prefix='/api')

@app.get("/static/walls")
def walls_page():
    return FileResponse("frontend/static/walls.html")


@app.get("/static/wall/new")
def new_wall_page():
    return FileResponse("frontend/static/wall_new.html")


@app.get("/static/wall/{wall_id}")
def wall_page(wall_id: int):
    return FileResponse("frontend/static/wall.html")

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/images", StaticFiles(directory="frontend/static/images"), name="images")
