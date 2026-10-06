"""Seed the Phase 2 console admin (idempotent).

Usage: `python scripts/seed_support_admin.py`
Creates `SUPPORT_ADMIN_EMAIL` / `SUPPORT_ADMIN_PASSWORD` (default
admin@shop.local / admin) with role SUPPORT_AGENT if missing.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "backend"), str(ROOT / "common"), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy.orm import Session  # noqa: E402

from app.services.auth import auth_service  # noqa: E402
from database.session import app_engine  # noqa: E402
from northstar_common.config import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    engine = app_engine()
    with Session(bind=engine) as session:
        profile = auth_service.ensure_support_admin(
            session,
            email=settings.support_admin_email,
            password=settings.support_admin_password,
        )
    print(f"support admin ready: {profile['email']} ({profile['role']})")


if __name__ == "__main__":
    main()
