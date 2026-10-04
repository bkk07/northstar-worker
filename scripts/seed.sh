#!/usr/bin/env bash
# Phase 5: load the deterministic seed world (idempotent; prints world hash).
# Usage: ./scripts/seed.sh  (or `make seed`)
set -euo pipefail

cd "$(dirname "$0")/.."
python -m database.seeds.loader seed
