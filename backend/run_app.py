import sys
import traceback
from pathlib import Path

# Добавить корень проекта в sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    try:
        from backend import app  # абсолютный импорт
    except Exception as e:
        print("Exception during app initialization:")
        traceback.print_exc()
        sys.exit(1)
