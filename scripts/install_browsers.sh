#!/usr/bin/env bash
# Phase 2: install the Chromium browser used by the Playwright layer.
# The browser module itself arrives in Phase 10; this keeps the
# download step ready for CI and fresh clones.
# Usage: ./scripts/install_browsers.sh
set -euo pipefail

python -m playwright install chromium --with-deps
