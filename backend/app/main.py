"""Backend app factory (Phase 1 skeleton).

Mounts controllers only; business logic lives in services/.
Run: `uvicorn app.main:app --app-dir backend --reload`
"""

from fastapi import FastAPI

from app.api import health_controller

APP_VERSION = "0.1.0-phase1"


def create_app() -> FastAPI:
    app = FastAPI(title="northstar-worker-backend", version=APP_VERSION)
    app.include_router(health_controller.router)
    return app


app = create_app()
