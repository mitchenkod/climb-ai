import traceback

if __name__ == "__main__":
    try:
        from fastapi import FastAPI
        from .db import models  # noqa: F401, force import for side effects
        app = FastAPI()
        print("App initialized successfully.")
    except Exception as e:
        print("Exception during app initialization:")
        traceback.print_exc()
        raise