from celery import Celery

from app.config import settings

celery = Celery(
    "riesgos",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Mexico_City",
    task_track_started=True,
    # Un contrato largo con OCR puede tardar: sin límite corto.
    task_soft_time_limit=1800,
    task_time_limit=2100,
    worker_max_tasks_per_child=20,
)
