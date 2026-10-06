# Phase 1 — local API container (10-phase spec §5-§6).
# Build context is the repo root (see docker-compose.yml).
# Dev default still runs: uvicorn app.main:app --app-dir backend --reload
FROM python:3.13-slim
WORKDIR /code
COPY pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir -e .
COPY backend/ ./backend/
COPY common/ ./common/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
