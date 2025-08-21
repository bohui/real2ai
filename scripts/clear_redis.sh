redis-cli --scan --pattern "celery-task-meta-*" | xargs redis-cli del
redis-cli --scan --pattern "task_auth:*" | xargs redis-cli del