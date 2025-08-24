#!/usr/bin/env bash
set -euo pipefail

echo "[reset] Restarting Redis via Docker Compose..."
( docker compose restart redis )

echo "[reset] Clearing backend data..."
( source backend/.venv/bin/activate && python backend/scripts/clear_data.py --yes )

echo "[reset] Clearing Redis keys via scripts/clear_redis.sh..."
# shellcheck source=/dev/null
source "scripts/clear_redis.sh"

echo "[reset] Done."


