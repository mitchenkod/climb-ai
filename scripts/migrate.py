import os
import sys
from pathlib import Path

# make sure imports from backend work when running from repo root
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.db.database import init_db

DB_PATH = "backend/app.db"


def migrate():
    if os.path.exists(DB_PATH):
        print(f"🧹 Removing existing database: {DB_PATH}")
        os.remove(DB_PATH)

    print("⚙️ Creating database schema from SQLModel metadata...")
    init_db()
    print("✅ Migration completed. DB schema is up to date.")


if __name__ == "__main__":
    migrate()
