from fastapi import FastAPI
from backend.db.database import init_db
from backend.api.gym import router as gym_router
from backend.api.wall import router as wall_router
from fastapi.staticfiles import StaticFiles

app = FastAPI()
@app.on_event("startup")
def on_startup():
    print("START BACKEND")
    init_db()
app.include_router(gym_router, prefix='/api')
app.include_router(wall_router, prefix='/api')
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
app.mount("/images", StaticFiles(directory="frontend/static/images"), name="images")