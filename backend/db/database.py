from sqlmodel import create_engine, SQLModel, Session
import backend.models

DATABSE_URL = "sqlite:///backend/app.db"

engine = create_engine(DATABSE_URL, echo=True)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session