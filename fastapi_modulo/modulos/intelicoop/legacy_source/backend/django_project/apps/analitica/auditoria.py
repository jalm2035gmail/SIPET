from __future__ import annotations

from collections.abc import Mapping

from django.db import DataMAINError

from .models import EventoAuditoria


def registrar_evento_auditoria(
    *,
    request=None,
    modulo: str,
    accion: str,
    resultado: str = EventoAuditoria.RESULTADO_OK,
    target_tipo: str = "",
    target_id: str = "",
    detalle: Mapping | None = None,
) -> None:
    user = getattr(request, "user", None) if request is not None else None
    is_auth = bool(user and getattr(user, "is_authenticated", False))
    actor = user if is_auth else None
    actor_username = getattr(user, "username", "") if is_auth else ""
    ip_origen = ""
    if request is not None:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded_for:
            ip_origen = forwarded_for.split(",")[0].strip()
        else:
            ip_origen = request.META.get("REMOTE_ADDR", "") or ""

    try:
        EventoAuditoria.objects.create(
            modulo=modulo,
            accion=accion,
            resultado=resultado,
            actor=actor,
            actor_username=actor_username,
            target_tipo=target_tipo,
            target_id=str(target_id or ""),
            ip_origen=ip_origen,
            detalle=dict(detalle or {}),
        )
    except DataMAINError:
        # Fail-open: la auditoria no debe romper el flujo transaccional principal.
        return
