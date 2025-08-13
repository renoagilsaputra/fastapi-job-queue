# celery_app.py - Celery Configuration
from celery import Celery
import os

# Redis URL (sesuaikan dengan setup Anda)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "fastapi_celery",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks']  # Include task modules
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Optional: Configure routing
celery_app.conf.task_routes = {
    'tasks.process_long_task': 'main-queue',
    'tasks.send_email_task': 'email-queue',
}