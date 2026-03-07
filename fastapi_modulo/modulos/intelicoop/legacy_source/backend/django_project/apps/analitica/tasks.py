from celery import shared_task

from .models import Campania, Prospecto


@shared_task
def generar_resumen_campanias() -> dict[str, int]:
    return {
        "campanias_total": Campania.objects.count(),
        "prospectos_total": Prospecto.objects.count(),
        "campanias_activas": Campania.objects.filter(estado=Campania.ESTADO_ACTIVA).count(),
    }
