#!/usr/bin/env bash
# Install the Chromium browser used by the Playwright layer (Phase 10).
# On Linux also run with --with-deps (needs sudo) for system libraries.
# Usage: ./scripts/install_browsers.sh
set -euo pipefail

python -m playwright install chromium
