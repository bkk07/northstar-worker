"""Backend app factory (Phase 6: commerce sandbox API).

Mounts controllers only; business logic lives in services/.
Run: `uvicorn app.main:app --app-dir backend --reload`
Docs: /docs (Swagger), /openapi.json (DTO source for the frontend).
"""

from fastapi import FastAPI

from app.api import health_controller
from app.api.commerce import read_controller, shop_controller
from app.api.control import chaos_controller, oracle_controller, reset_controller
from app.api.ops import (
    auth_controller,
    customer_controller,
    note_controller,
    order_controller,
    refund_controller,
    replacement_controller,
    reply_controller,
    status_controller,
    ticket_controller,
)
from app.api.worker import approval_controller, clarification_controller, task_controller
from app.core.exceptions import AppError, app_error_handler

APP_VERSION = "0.1.0-phase6"


def create_app() -> FastAPI:
    """Assemble the FastAPI app with every commerce router."""
    app = FastAPI(title="northstar-worker-backend", version=APP_VERSION)
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(health_controller.router)
    app.include_router(read_controller.router)
    app.include_router(shop_controller.router)
    app.include_router(auth_controller.router)
    app.include_router(ticket_controller.router)
    app.include_router(customer_controller.router)
    app.include_router(order_controller.router)
    app.include_router(replacement_controller.router)
    app.include_router(refund_controller.router)
    app.include_router(note_controller.router)
    app.include_router(reply_controller.router)
    app.include_router(status_controller.router)
    app.include_router(chaos_controller.router)
    app.include_router(reset_controller.router)
    app.include_router(oracle_controller.router)
    app.include_router(task_controller.router)
    app.include_router(approval_controller.router)
    app.include_router(clarification_controller.router)
    return app


app = create_app()
