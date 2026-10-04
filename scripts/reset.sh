#!/usr/bin/env bash
# Phase 5: truncate all biz/worker tables (admin role). Seeds are reloaded
# with ./scripts/seed.sh; `reset && seed` reproduces an identical world hash.
# Usage: ./scripts/reset.sh  (or `make reset`)
set -euo pipefail

cd "$(dirname "$0")/.."
python -m database.seeds.loader reset
