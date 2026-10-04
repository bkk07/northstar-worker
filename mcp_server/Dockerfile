# MCP tool server image (Phase 11): typed boundary, no DB credentials.
# Reads go through the backend read API; writes go through hosted Chromium.
FROM python:3.12-slim

WORKDIR /srv
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi httpx "mcp>=1.0" playwright pydantic \
    && python -m playwright install chromium --with-deps

COPY common/ ./common/
COPY browser/ ./browser/
COPY mcp_server/ ./mcp_server/

ENV PYTHONPATH="/srv/common" \
    READ_API_URL="http://backend:8000" \
    FRONTEND_URL="http://frontend:5173" \
    MCP_PORT="8002"

EXPOSE 8002
CMD ["python", "-m", "mcp_server.server"]
