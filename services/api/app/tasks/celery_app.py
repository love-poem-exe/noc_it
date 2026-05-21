import os
from celery import Celery
from app.core.config import settings

# Enable a local "eager" mode for development when CELERY_TASKS_ALWAYS_EAGER
# environment variable is set (1/true/yes). In eager mode tasks run locally
# and use an in-memory backend so Redis/Docker is not required for testing.
_EAGER = os.getenv("CELERY_TASKS_ALWAYS_EAGER", "0").lower() in ("1", "true", "yes")

if _EAGER:
    celery_app = Celery("noc_tasks", broker="memory://", backend="cache+memory://")
else:
    celery_app = Celery(
        "noc_tasks",
        broker=settings.redis_url,
        backend=settings.redis_url,
    )

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

if _EAGER:
    celery_app.conf.update(
        task_always_eager=True,
        task_store_eager_result=True,
    )
