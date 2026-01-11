"""Celery application configuration."""

import os

from celery import Celery

# Get broker URL from environment
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# Create Celery app
app = Celery(
    "lecpa_worker",
    broker=broker_url,
    backend=result_backend,
    include=[
        "tasks.ingest",
        "tasks.extract",
        "tasks.canonicalize",
        "tasks.ocr",
        "tasks.embed",
        "tasks.field_extraction",
    ],
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit at 9 minutes
    worker_prefetch_multiplier=1,  # Process one task at a time
    task_acks_late=True,  # Acknowledge after task completes
    task_reject_on_worker_lost=True,
)

# Task routing
app.conf.task_routes = {
    "tasks.ingest.*": {"queue": "ingest"},
    "tasks.extract.*": {"queue": "extract"},
    "tasks.ocr.*": {"queue": "ocr"},
    "tasks.embed.*": {"queue": "embed"},
    "tasks.field_extraction.*": {"queue": "field_extraction"},
}

if __name__ == "__main__":
    app.start()
