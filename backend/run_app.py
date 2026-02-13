import sys
import traceback

if __name__ == "__main__":
    try:
        from backend import app  # абсолютный импорт
    except Exception as e:
        print("Exception during app initialization:")
        traceback.print_exc()
        sys.exit(1)
