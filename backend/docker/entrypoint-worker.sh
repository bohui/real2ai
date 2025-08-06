#!/bin/bash
set -e

# Environment variables with defaults
WORKER_TYPE=${WORKER_TYPE:-"worker"}
CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-"2"}
CELERY_QUEUES=${CELERY_QUEUES:-"evaluation,batch,ab_tests,reports,maintenance,monitoring,cache"}
LOG_LEVEL=${LOG_LEVEL:-"INFO"}

# Wait for dependencies
echo "Waiting for Redis..."
python -c "
import redis
import time
import os
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
r = redis.Redis.from_url(redis_url)
while True:
    try:
        r.ping()
        print('Redis is ready!')
        break
    except redis.ConnectionError:
        print('Redis not ready, waiting...')
        time.sleep(1)
"

echo "Waiting for Database..."
python -c "
import asyncio
import os
import sys
import time
sys.path.append('/app')

async def wait_for_db():
    from app.dependencies.supabase import get_supabase_client
    while True:
        try:
            client = await get_supabase_client()
            result = await client.table('evaluation_jobs').select('id').limit(1).execute()
            print('Database is ready!')
            break
        except Exception as e:
            print(f'Database not ready: {e}, waiting...')
            time.sleep(2)

asyncio.run(wait_for_db())
"

# Initialize monitoring
echo "Initializing monitoring..."
python -c "
import sys
sys.path.append('/app')
from app.monitoring.evaluation_monitoring import get_monitor
monitor = get_monitor()
print('Monitoring initialized')
"

case "$1" in
    "worker")
        echo "Starting Celery worker..."
        exec celery -A app.tasks.evaluation_tasks worker \
            --loglevel=$LOG_LEVEL \
            --concurrency=$CELERY_CONCURRENCY \
            --queues=$CELERY_QUEUES \
            --max-tasks-per-child=1000 \
            --time-limit=1800 \
            --soft-time-limit=1500 \
            --prefetch-multiplier=1
        ;;
    "beat")
        echo "Starting Celery beat scheduler..."
        exec celery -A app.tasks.evaluation_tasks beat \
            --loglevel=$LOG_LEVEL \
            --schedule=/app/data/celerybeat-schedule \
            --pidfile=/app/data/celerybeat.pid
        ;;
    "flower")
        echo "Starting Flower monitoring..."
        exec celery -A app.tasks.evaluation_tasks flower \
            --port=5555 \
            --url_prefix=/flower
        ;;
    "priority-worker")
        echo "Starting high-priority worker..."
        exec celery -A app.tasks.evaluation_tasks worker \
            --loglevel=$LOG_LEVEL \
            --concurrency=1 \
            --queues=evaluation \
            --max-tasks-per-child=100 \
            --time-limit=3600 \
            --soft-time-limit=3300 \
            --prefetch-multiplier=1
        ;;
    *)
        echo "Usage: $0 {worker|beat|flower|priority-worker}"
        exit 1
        ;;
esac