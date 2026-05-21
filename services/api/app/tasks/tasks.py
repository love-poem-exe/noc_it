from app.tasks.celery_app import celery_app
from app.services.script_runner import run_script


@celery_app.task(name="scripts.run")
def run_script_task(script: str, method: str, payload: dict | None = None) -> dict:
    return run_script(script, method, payload)
