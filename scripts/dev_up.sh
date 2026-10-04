#!/usr/bin/env bash
# Phase 2: bring up local infrastructure (Postgres container).
# Usage: ./scripts/dev_up.sh
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "No .env found; copying from .env.example (edit secrets afterwards)."
  cp .env.example .env
fi

docker compose up -d
echo "Waiting for Postgres to become healthy..."
until docker exec northstar-postgres pg_isready -U postgres -d northstar >/dev/null 2>&1; do
  sleep 1
done
echo "Postgres is up (northstar DB, empty until Phase 4 migrations)."
