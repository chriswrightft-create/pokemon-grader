#!/bin/zsh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${0}")" && pwd)"
VENV_BIN="$PROJECT_DIR/.venv/bin"

cd "$PROJECT_DIR"
exec "$VENV_BIN/streamlit" run "app.py" \
  --server.headless true \
  --server.address 127.0.0.1 \
  --server.port 8510 \
  --browser.gatherUsageStats false
