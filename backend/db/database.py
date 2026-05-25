from sqlalchemy import text
from sqlmodel import create_engine, SQLModel, Session
import backend.models

DATABSE_URL = "sqlite:///backend/app.db"

engine = create_engine(DATABSE_URL, echo=True)

def init_db():
    SQLModel.metadata.create_all(engine)
    ensure_schema_patches()


def ensure_schema_patches():
    """Apply small SQLite-compatible patches for existing dev databases."""
    with engine.begin() as connection:
        wall_columns = table_columns(connection, "wall")
        if "image_name" not in wall_columns:
            connection.execute(
                text("ALTER TABLE wall ADD COLUMN image_name VARCHAR NOT NULL DEFAULT 'wall.jpg'")
            )

        surface_columns = table_columns(connection, "surface")
        add_column(connection, surface_columns, "surface", "width_m", "FLOAT NOT NULL DEFAULT 1.0")
        add_column(connection, surface_columns, "surface", "height_m", "FLOAT NOT NULL DEFAULT 1.0")
        add_column(connection, surface_columns, "surface", "image_width_px", "INTEGER NOT NULL DEFAULT 1")
        add_column(connection, surface_columns, "surface", "image_height_px", "INTEGER NOT NULL DEFAULT 1")

        hold_columns = table_columns(connection, "hold")
        add_column(connection, hold_columns, "hold", "x_px", "FLOAT")
        add_column(connection, hold_columns, "hold", "y_px", "FLOAT")
        add_column(connection, hold_columns, "hold", "x_m", "FLOAT")
        add_column(connection, hold_columns, "hold", "y_m", "FLOAT")


def table_columns(connection, table_name):
    columns = connection.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {column[1] for column in columns}


def add_column(connection, existing_columns, table_name, column_name, column_definition):
    if column_name not in existing_columns:
        connection.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
        )

def get_session():
    with Session(engine) as session:
        yield session
