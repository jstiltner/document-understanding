import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Create Celery instance
celery_app = Celery(
    "doc_processing",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=["tasks.document_processing", "tasks.batch_processing", "tasks.monitoring"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    task_routes={
        "tasks.document_processing.process_document": {"queue": "document_processing"},
        "tasks.batch_processing.process_batch": {"queue": "batch_processing"},
        "tasks.monitoring.collect_metrics": {"queue": "monitoring"},
    },
    beat_schedule={
        "collect-system-metrics": {
            "task": "tasks.monitoring.collect_metrics",
            "schedule": 60.0,  # Every minute
        },
        "cleanup-old-tasks": {
            "task": "tasks.monitoring.cleanup_old_tasks",
            "schedule": 3600.0,  # Every hour
        },
    },
)

if __name__ == "__main__":
    celery_app.start()