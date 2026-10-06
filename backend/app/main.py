"""Backend app factory (Phase 6: commerce sandbox API).

Mounts controllers only; business logic lives in services/.
Run: `uvicorn app.main:app --app-dir backend --reload`
Docs: /docs (Swagger), /openapi.json (DTO source for the frontend).
"""

from fastapi import FastAPI

from app.api import health_controller
from app.api.agent import direct_controller
from app.api.agentrun import agent_controller as phase9_agent_controller
from app.api.auth import auth_controller as phase2_auth_controller
from app.api.commerce import catalog_controller, read_controller, shop_controller
from app.api.control import chaos_controller, oracle_controller, reset_controller
from app.api.evaluation import evaluation_controller
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
from app.api.orders import orders_controller as phase4_orders_controller
from app.api.products import products_controller as phase3_products_controller
from app.api.support import support_controller as phase6_support_controller
from app.api.tickets import tickets_controller as phase5_tickets_controller
from app.api.worker import (
    approval_controller,
    chat_controller,
    clarification_controller,
    environment_controller,
    events_controller,
    evidence_controller,
    memory_controller,
    task_controller,
    verification_controller,
)
from app.core.exceptions import AppError, app_error_handler

APP_VERSION = "0.1.0-phase6"


def create_app() -> FastAPI:
    """Assemble the FastAPI app with every commerce router."""
    app = FastAPI(title="northstar-worker-backend", version=APP_VERSION)
    app.add_exception_handler(AppError, app_error_handler)
    app.include_router(phase2_auth_controller.router)
    app.include_router(phase3_products_controller.router)
    app.include_router(phase4_orders_controller.router)
    app.include_router(phase5_tickets_controller.router)
    app.include_router(phase6_support_controller.router)
    app.include_router(phase9_agent_controller.router)
    app.include_router(health_controller.router)
    app.include_router(direct_controller.router)
    app.include_router(read_controller.router)
    app.include_router(catalog_controller.router)
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
    app.include_router(evaluation_controller.router)
    app.include_router(task_controller.router)
    app.include_router(chat_controller.router)
    app.include_router(approval_controller.router)
    app.include_router(clarification_controller.router)
    app.include_router(memory_controller.router)
    app.include_router(environment_controller.router)
    app.include_router(events_controller.router)
    app.include_router(evidence_controller.router)
    app.include_router(verification_controller.router)
    return app


app = create_app()
