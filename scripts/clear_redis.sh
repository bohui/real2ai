#!/usr/bin/env bash
set -euo pipefail

# Load env for REDIS_URL if present
if [ -f ./.env.local ]; then
  set -a
  # shellcheck disable=SC1091
  source ./.env.local
  set +a
fi

_redis_cli() {
  # Prefer Docker Compose Redis container
  if docker compose ps --services 2>/dev/null | grep -q "^redis$"; then
    docker compose exec -T redis redis-cli "$@"
    return
  fi
  # Fall back to REDIS_URL if defined
  if [ -n "${REDIS_URL:-}" ]; then
    redis-cli -u "$REDIS_URL" "$@"
    return
  fi
  # Default local redis-cli
  redis-cli "$@"
}

_del_keys_chunked() {
  # delete keys passed as args in chunks to avoid argv limits
  local chunk_size=100
  local total=$#
  local start=1
  while [ $start -le $total ]; do
    # shellcheck disable=SC2206
    local keys=("${@:start:chunk_size}")
    if [ ${#keys[@]} -gt 0 ]; then
      _redis_cli DEL "${keys[@]}" >/dev/null || true
    fi
    start=$((start + chunk_size))
  done
}

delete_pattern() {
  local pattern="$1"
  local key
  local key_list=()
  while IFS= read -r key; do
    [ -n "$key" ] && key_list+=("$key")
  done < <(_redis_cli --scan --pattern "$pattern" COUNT 10000 || true)
  if [ ${#key_list[@]} -gt 0 ]; then
    _del_keys_chunked "${key_list[@]}"
  fi
}

echo "[clear_redis] Deleting Redis keys by pattern..."
delete_pattern "task_auth:*"
delete_pattern "celery-task-meta-*"
delete_pattern "celery*" # queues, control, results
echo "[clear_redis] Done."
