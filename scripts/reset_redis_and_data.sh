#!/usr/bin/env bash
set -euo pipefail

# Load environment (including .env.local) so Celery and Python pick up correct settings
if [ -f .env.local ]; then
  echo "[reset] Loading environment from .env.local"
  set -a
  # shellcheck disable=SC1091
  source ./.env.local
  set +a
fi

echo "[reset] Restarting Redis via Docker Compose..."
( docker compose restart redis | cat )

echo "[reset] Flushing Redis (all DBs) inside container..."
# Use FLUSHALL for a truly clean environment (safe here as this Redis is project-scoped)
flush_ok=false
if docker compose exec -T redis redis-cli PING >/dev/null 2>&1; then
  if docker compose exec -T redis redis-cli FLUSHALL | cat; then
    flush_ok=true
  fi
else
  echo "[reset] Redis container not ready yet; retrying FLUSHALL after short wait..."
  sleep 2
  if docker compose exec -T redis redis-cli FLUSHALL | cat; then
    flush_ok=true
  fi
fi

echo "[reset] Purging Celery queues (broker: ${REDIS_URL:-redis://localhost:6379})..."
# Purge via Celery to ensure no stale enqueued tasks remain referencing old context keys
(
  cd backend && \
  source .venv/bin/activate && \
  celery -A app.core.celery purge -f | cat || true
)

echo "[reset] Clearing backend data (database and storage buckets)..."
(
  source backend/.venv/bin/activate && \
  python backend/scripts/clear_data.py --yes | cat
)

if [ "$flush_ok" != true ]; then
  echo "[reset] Performing targeted Redis cleanup (keys) (FLUSHALL not confirmed)..."
  # shellcheck source=/dev/null
  source "scripts/clear_redis.sh"
else
  echo "[reset] Skipping targeted Redis cleanup: FLUSHALL succeeded."
fi

echo "[reset] Done."


