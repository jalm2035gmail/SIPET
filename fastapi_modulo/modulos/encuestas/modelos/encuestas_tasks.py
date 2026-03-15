from __future__ import annotations

import os
from typing import Any, Dict, Optional

from celery import Celery


def _broker_url() -> str:
    return (
        os.environ.get("ENCUESTAS_CELERY_BROKER_URL")
        or os.environ.get("CELERY_BROKER_URL")
        or os.environ.get("REDIS_URL")
        or "redis://localhost:6379/0"
    ).strip()


def _result_backend() -> str:
    return (
        os.environ.get("ENCUESTAS_CELERY_RESULT_BACKEND")
        or os.environ.get("CELERY_RESULT_BACKEND")
        or _broker_url()
    ).strip()


def get_celery_app() -> Celery:
    app = Celery(
        "sipet_encuestas",
        broker=_broker_url(),
        backend=_result_backend(),
        include=["fastapi_modulo.modulos.encuestas.modelos.encuestas_tasks"],
    )
    app.conf.task_default_queue = (os.environ.get("ENCUESTAS_CELERY_QUEUE") or "encuestas_automation").strip() or "encuestas_automation"
    app.conf.task_serializer = "json"
    app.conf.accept_content = ["json"]
    app.conf.result_serializer = "json"
    app.conf.timezone = "UTC"
    return app


celery_app = get_celery_app()


@celery_app.task(name="encuestas.run_automation_jobs")
def run_automation_jobs_task(tenant_id: str, instance_id: Optional[int] = None) -> Dict[str, Any]:
    from fastapi_modulo.modulos.encuestas.modelos.encuestas_store import run_automation_jobs

    return run_automation_jobs(tenant_id, instance_id=instance_id)


@celery_app.task(name="encuestas.dispatch_backendhook")
def dispatch_backendhook_task(
    tenant_id: str,
    instance_id: int,
    event_name: str,
    payload: Dict[str, Any],
    assignment_id: Optional[int] = None,
) -> Dict[str, Any]:
    from fastapi_modulo.modulos.encuestas.modelos.encuestas_store import dispatch_backendhook_event

    return dispatch_backendhook_event(
        tenant_id=tenant_id,
        instance_id=instance_id,
        event_name=event_name,
        payload=payload,
        assignment_id=assignment_id,
    )
