from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError

from fastapi_modulo.modulos.capacitacion.controladores.dependencies import load_colab_meta
from fastapi_modulo.modulos.capacitacion.repositorios import gamificacion_repository as repo

NIVELES = [(0, "🌱", "Aprendiz"), (100, "📖", "Practicante"), (300, "⚡", "Avanzado"), (700, "🎓", "Experto"), (1500, "🏆", "Maestro")]
INSIGNIAS_DEFAULT = [
    {"nombre": "Primer paso", "descripcion": "Completa tu primera leccion.", "icono_emoji": "🎯", "condicion_tipo": "lecciones_completadas", "condicion_valor": 1, "color": "#6366f1", "orden": 1},
    {"nombre": "Estudioso", "descripcion": "Completa 10 lecciones.", "icono_emoji": "📚", "condicion_tipo": "lecciones_completadas", "condicion_valor": 10, "color": "#2563eb", "orden": 2},
    {"nombre": "Voraz del conocimiento", "descripcion": "Completa 25 lecciones.", "icono_emoji": "🧠", "condicion_tipo": "lecciones_completadas", "condicion_valor": 25, "color": "#9333ea", "orden": 3},
    {"nombre": "Primer curso", "descripcion": "Completa tu primer curso.", "icono_emoji": "✅", "condicion_tipo": "cursos_completados", "condicion_valor": 1, "color": "#16a34a", "orden": 4},
    {"nombre": "Constante", "descripcion": "Completa 3 cursos.", "icono_emoji": "🔥", "condicion_tipo": "cursos_completados", "condicion_valor": 3, "color": "#ea580c", "orden": 5},
    {"nombre": "Maestro del aprendizaje", "descripcion": "Completa 5 cursos.", "icono_emoji": "🏆", "condicion_tipo": "cursos_completados", "condicion_valor": 5, "color": "#b45309", "orden": 6},
    {"nombre": "Graduado", "descripcion": "Obten tu primer certificado.", "icono_emoji": "🎓", "condicion_tipo": "certificados_obtenidos", "condicion_valor": 1, "color": "#0891b2", "orden": 7},
    {"nombre": "Coleccionista", "descripcion": "Obten 3 certificados.", "icono_emoji": "💎", "condicion_tipo": "certificados_obtenidos", "condicion_valor": 3, "color": "#0e7490", "orden": 8},
    {"nombre": "Perfeccionista", "descripcion": "Obten 100% en una evaluacion.", "icono_emoji": "⭐", "condicion_tipo": "puntaje_perfecto", "condicion_valor": 1, "color": "#ca8a04", "orden": 9},
    {"nombre": "Racha 5", "descripcion": "Mantiene una racha de 5 dias.", "icono_emoji": "🔥", "condicion_tipo": "racha_dias", "condicion_valor": 5, "color": "#dc2626", "orden": 10},
    {"nombre": "Primer intento", "descripcion": "Aprueba una evaluacion al primer intento.", "icono_emoji": "🥇", "condicion_tipo": "primer_intento_aprobado", "condicion_valor": 1, "color": "#0f766e", "orden": 11},
]

RETOS_MENSUALES = [
    {"codigo": "reto_lecciones", "nombre": "Reto mensual de lecciones", "descripcion": "Completa 5 lecciones este mes.", "motivo": "leccion_completada", "meta": 5, "recompensa": 40},
    {"codigo": "reto_primer_intento", "nombre": "Aprobacion al primer intento", "descripcion": "Aprueba 1 evaluacion al primer intento este mes.", "motivo": "aprobado_primer_intento", "meta": 1, "recompensa": 35},
    {"codigo": "reto_constancia", "nombre": "Semana de constancia", "descripcion": "Suma actividad positiva en 7 dias del mes.", "motivo": "constancia_diaria", "meta": 7, "recompensa": 30},
]


def _utcnow():
    return datetime.utcnow()


def _month_bounds(ref=None):
    ref = ref or _utcnow()
    start = ref.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return start, next_month - timedelta(microseconds=1)


def _season_payload(ref=None):
    ref = ref or _utcnow()
    quarter = ((ref.month - 1) // 3) + 1
    start_month = ((quarter - 1) * 3) + 1
    start = ref.replace(month=start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    if start_month == 10:
        end = start.replace(year=start.year + 1, month=1) - timedelta(microseconds=1)
    else:
        end = start.replace(month=start_month + 3) - timedelta(microseconds=1)
    return {
        "codigo": f"{ref.year}-Q{quarter}",
        "nombre": f"Temporada Q{quarter} {ref.year}",
        "fecha_inicio": start.isoformat(),
        "fecha_fin": end.isoformat(),
    }


def _get_nivel(puntos):
    nivel_actual = NIVELES[0]
    for umbral, emoji, nombre in NIVELES:
        if puntos >= umbral:
            nivel_actual = (umbral, emoji, nombre)
    idx = next(i for i, item in enumerate(NIVELES) if item[0] == nivel_actual[0])
    if idx < len(NIVELES) - 1:
        siguiente = NIVELES[idx + 1]
        pct = round((puntos - nivel_actual[0]) / (siguiente[0] - nivel_actual[0]) * 100)
    else:
        siguiente = (None, None, None)
        pct = 100
    return {"nivel": nivel_actual[2], "emoji": nivel_actual[1], "pts_siguiente": siguiente[0], "nombre_siguiente": siguiente[2], "pct_nivel": max(0, min(pct, 100))}


def _seed_insignias(db, tenant_id):
    if repo.count_insignias(db, tenant_id) > 0:
        return
    base_tenant = "default"
    if tenant_id != base_tenant and repo.count_insignias(db, base_tenant) == 0:
        for data in INSIGNIAS_DEFAULT:
            repo.create_insignia(db, {**data, "tenant_id": base_tenant})
    if tenant_id != base_tenant:
        for ins in repo.list_insignias(db, base_tenant):
            repo.create_insignia(
                db,
                {
                    "tenant_id": tenant_id,
                    "nombre": ins.nombre,
                    "descripcion": ins.descripcion,
                    "icono_emoji": ins.icono_emoji,
                    "condicion_tipo": ins.condicion_tipo,
                    "condicion_valor": ins.condicion_valor,
                    "color": ins.color,
                    "orden": ins.orden,
                },
            )
    else:
        for data in INSIGNIAS_DEFAULT:
            repo.create_insignia(db, {**data, "tenant_id": tenant_id})
    db.commit()


def _activity_days(logs):
    days = sorted({item.fecha.date() for item in logs if item.fecha})
    return days


def _streak_metrics(logs):
    days = _activity_days(logs)
    if not days:
        return {"streak_actual": 0, "streak_maximo": 0}
    max_streak = current = 1
    for idx in range(1, len(days)):
        delta = (days[idx] - days[idx - 1]).days
        if delta == 1:
            current += 1
        elif delta > 1:
            current = 1
        max_streak = max(max_streak, current)
    current_streak = 1
    today = _utcnow().date()
    if days[-1] < today - timedelta(days=1):
        current_streak = 0
    else:
        for idx in range(len(days) - 1, 0, -1):
            delta = (days[idx] - days[idx - 1]).days
            if delta == 1:
                current_streak += 1
            else:
                break
    return {"streak_actual": current_streak, "streak_maximo": max_streak}


def _count_badge_condition(db, colaborador_key, tenant_id, condicion_tipo):
    if condicion_tipo in {"lecciones_completadas", "cursos_completados", "certificados_obtenidos", "puntaje_perfecto"}:
        return repo.count_condicion(db, colaborador_key, condicion_tipo, tenant_id)
    if condicion_tipo == "racha_dias":
        return _streak_metrics(repo.list_puntos_logs(db, colaborador_key, tenant_id, positivos_solo=True))["streak_maximo"]
    if condicion_tipo == "primer_intento_aprobado":
        logs = repo.list_puntos_logs(db, colaborador_key, tenant_id, positivos_solo=False)
        return sum(1 for item in logs if item.motivo == "aprobado_primer_intento")
    return 0


def _ensure_daily_consistency_bonus(db, colaborador_key, tenant_id, fecha):
    if not fecha:
        return
    day_ref = int(fecha.strftime("%Y%m%d"))
    existing = repo.get_puntos_log(db, tenant_id, colaborador_key, "constancia_diaria", "streak_day", day_ref)
    if existing:
        return
    start = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1) - timedelta(microseconds=1)
    logs = repo.list_puntos_logs(db, colaborador_key, tenant_id, positivos_solo=True, fecha_desde=start, fecha_hasta=end)
    if len(logs) == 1:
        repo.create_puntos_log(
            db,
            {
                "tenant_id": tenant_id,
                "colaborador_key": colaborador_key,
                "puntos": 5,
                "motivo": "constancia_diaria",
                "referencia_tipo": "streak_day",
                "referencia_id": day_ref,
                "fecha": fecha,
            },
        )


def _apply_abandonment_penalties(db, colaborador_key, tenant_id):
    limite = _utcnow() - timedelta(days=14)
    penalized = 0
    for insc in repo.list_inscripciones_en_progreso(db, colaborador_key, tenant_id, updated_before=limite):
        existing = repo.get_puntos_log(db, tenant_id, colaborador_key, "abandono_curso", "inscripcion", insc.id)
        if existing:
            continue
        repo.create_puntos_log(
            db,
            {
                "tenant_id": tenant_id,
                "colaborador_key": colaborador_key,
                "puntos": -15,
                "motivo": "abandono_curso",
                "referencia_tipo": "inscripcion",
                "referencia_id": insc.id,
                "fecha": _utcnow(),
            },
        )
        penalized += 1
    if penalized:
        db.commit()


def _monthly_challenges(db, colaborador_key, tenant_id):
    start, end = _month_bounds()
    logs = repo.list_puntos_logs(db, colaborador_key, tenant_id, positivos_solo=False, fecha_desde=start, fecha_hasta=end)
    counters = {}
    for item in logs:
        counters[item.motivo] = counters.get(item.motivo, 0) + 1
    retos = []
    for reto in RETOS_MENSUALES:
        progreso = counters.get(reto["motivo"], 0)
        reto_ref = int(start.strftime("%Y%m"))
        completado = progreso >= reto["meta"]
        if completado and not repo.get_puntos_log(db, tenant_id, colaborador_key, f'{reto["codigo"]}_completado', "reto_mensual", reto_ref):
            repo.create_puntos_log(
                db,
                {
                    "tenant_id": tenant_id,
                    "colaborador_key": colaborador_key,
                    "puntos": reto["recompensa"],
                    "motivo": f'{reto["codigo"]}_completado',
                    "referencia_tipo": "reto_mensual",
                    "referencia_id": reto_ref,
                    "fecha": _utcnow(),
                },
            )
        retos.append({**reto, "progreso": progreso, "completado": completado})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return retos


def _scope_map(db, tenant_id, scope):
    if scope == "empresa":
        return {}
    meta = load_colab_meta() if scope in {"area", "sucursal"} else {}
    latest = repo.list_ultima_inscripcion_por_colaborador(db, tenant_id)
    result = {}
    for colaborador_key, insc in latest.items():
        if scope == "departamento":
            result[colaborador_key] = insc.departamento or "Sin departamento"
        elif scope in {"area", "sucursal"}:
            row = meta.get(str(colaborador_key), {}) if isinstance(meta, dict) else {}
            if not row:
                row = meta.get(str(getattr(insc, "colaborador_key", "")), {}) if isinstance(meta, dict) else {}
            result[colaborador_key] = row.get(scope) or row.get(f"{scope}_nombre") or "Sin " + scope
    return result


def otorgar_puntos(colaborador_key, motivo, puntos, referencia_tipo=None, referencia_id=None, tenant_id="default"):
    db = repo.get_db()
    try:
        now = _utcnow()
        repo.create_puntos_log(
            db,
            {
                "tenant_id": tenant_id,
                "colaborador_key": colaborador_key,
                "puntos": puntos,
                "motivo": motivo,
                "referencia_tipo": referencia_tipo,
                "referencia_id": referencia_id,
                "fecha": now,
            },
        )
        if puntos > 0 and motivo not in {"constancia_diaria"}:
            _ensure_daily_consistency_bonus(db, colaborador_key, tenant_id, now)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        return get_puntos_totales(colaborador_key, tenant_id=tenant_id)
    finally:
        db.close()


def get_puntos_totales(colaborador_key, tenant_id="default"):
    db = repo.get_db()
    try:
        _apply_abandonment_penalties(db, colaborador_key, tenant_id)
        return int(repo.get_puntos_sum(db, colaborador_key, tenant_id) or 0)
    finally:
        db.close()


def check_y_otorgar_insignias(colaborador_key, tenant_id="default"):
    db = repo.get_db()
    try:
        _seed_insignias(db, tenant_id)
        nuevas = []
        ya_tiene = {item.insignia_id for item in repo.list_colaborador_insignias(db, colaborador_key, tenant_id)}
        for insignia in repo.list_insignias(db, tenant_id):
            if insignia.id in ya_tiene:
                continue
            if _count_badge_condition(db, colaborador_key, tenant_id, insignia.condicion_tipo) >= insignia.condicion_valor:
                repo.create_colaborador_insignia(db, {"tenant_id": tenant_id, "colaborador_key": colaborador_key, "insignia_id": insignia.id, "fecha_obtencion": _utcnow()})
                nuevas.append({"id": insignia.id, "nombre": insignia.nombre, "descripcion": insignia.descripcion, "icono_emoji": insignia.icono_emoji, "color": insignia.color})
        if nuevas:
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
        return nuevas
    finally:
        db.close()


def get_insignias_disponibles(tenant_id="default"):
    db = repo.get_db()
    try:
        _seed_insignias(db, tenant_id)
        return [{"id": item.id, "nombre": item.nombre, "descripcion": item.descripcion, "icono_emoji": item.icono_emoji, "condicion_tipo": item.condicion_tipo, "condicion_valor": item.condicion_valor, "color": item.color, "orden": item.orden} for item in repo.list_insignias(db, tenant_id)]
    finally:
        db.close()


def crear_insignia(data, tenant_id="default"):
    db = repo.get_db()
    try:
        _seed_insignias(db, tenant_id)
        obj = repo.create_insignia(db, {**data, "tenant_id": tenant_id})
        db.commit()
        db.refresh(obj)
        return {"id": obj.id, "nombre": obj.nombre, "descripcion": obj.descripcion, "icono_emoji": obj.icono_emoji, "condicion_tipo": obj.condicion_tipo, "condicion_valor": obj.condicion_valor, "color": obj.color, "orden": obj.orden}
    finally:
        db.close()


def actualizar_insignia(insignia_id, data, tenant_id="default"):
    db = repo.get_db()
    try:
        obj = repo.get_insignia(db, insignia_id, tenant_id)
        if not obj:
            return None
        for field, value in data.items():
            if hasattr(obj, field) and value is not None:
                setattr(obj, field, value)
        db.commit()
        db.refresh(obj)
        return {"id": obj.id, "nombre": obj.nombre, "descripcion": obj.descripcion, "icono_emoji": obj.icono_emoji, "condicion_tipo": obj.condicion_tipo, "condicion_valor": obj.condicion_valor, "color": obj.color, "orden": obj.orden}
    finally:
        db.close()


def eliminar_insignia(insignia_id, tenant_id="default"):
    db = repo.get_db()
    try:
        obj = repo.get_insignia(db, insignia_id, tenant_id)
        if not obj:
            return False
        db.delete(obj)
        db.commit()
        return True
    finally:
        db.close()


def get_mis_insignias(colaborador_key, tenant_id="default"):
    db = repo.get_db()
    try:
        _seed_insignias(db, tenant_id)
        result = []
        for entry in repo.list_colaborador_insignias(db, colaborador_key, tenant_id):
            ins = entry.insignia
            result.append({"id": ins.id, "nombre": ins.nombre, "descripcion": ins.descripcion, "icono_emoji": ins.icono_emoji, "color": ins.color, "orden": ins.orden, "fecha_obtencion": entry.fecha_obtencion.isoformat() if entry.fecha_obtencion else None})
        return sorted(result, key=lambda item: item["orden"])
    finally:
        db.close()


def get_perfil_gamificacion(colaborador_key, tenant_id="default"):
    db = repo.get_db()
    try:
        _seed_insignias(db, tenant_id)
        _apply_abandonment_penalties(db, colaborador_key, tenant_id)
        retos = _monthly_challenges(db, colaborador_key, tenant_id)
        puntos = int(repo.get_puntos_sum(db, colaborador_key, tenant_id) or 0)
        actividad_rows = repo.list_puntos_logs(db, colaborador_key, tenant_id, positivos_solo=False)
        actividad = [{"puntos": item.puntos, "motivo": item.motivo, "fecha": item.fecha.isoformat() if item.fecha else None} for item in sorted(actividad_rows, key=lambda row: row.fecha or _utcnow(), reverse=True)[:10]]
        streak = _streak_metrics([item for item in actividad_rows if item.puntos > 0])
    finally:
        db.close()
    return {
        "colaborador_key": colaborador_key,
        "puntos_totales": puntos,
        **_get_nivel(puntos),
        **streak,
        "temporada_actual": _season_payload(),
        "retos_mensuales": retos,
        "insignias": get_mis_insignias(colaborador_key, tenant_id),
        "actividad_reciente": actividad,
    }


def get_ranking(limit=10, tenant_id="default", scope="empresa", value=None, season="actual"):
    db = repo.get_db()
    try:
        fecha_desde = fecha_hasta = None
        if season == "actual":
            quarter = _season_payload()
            fecha_desde = datetime.fromisoformat(quarter["fecha_inicio"])
            fecha_hasta = datetime.fromisoformat(quarter["fecha_fin"])
        rows = repo.ranking_rows(db, limit * 4, tenant_id, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
        scope_map = _scope_map(db, tenant_id, scope)
        result = []
        for row in rows:
            ck = row[0]
            if scope != "empresa":
                label = scope_map.get(ck)
                if value and label != value:
                    continue
            pts = int(row[1] or 0)
            nivel = _get_nivel(pts)
            nombre = repo.get_colaborador_nombre(db, ck, tenant_id)
            result.append(
                {
                    "posicion": len(result) + 1,
                    "colaborador_key": ck,
                    "colaborador_nombre": nombre[0] if nombre else ck,
                    "puntos": pts,
                    "nivel": nivel["nivel"],
                    "emoji_nivel": nivel["emoji"],
                    "num_insignias": repo.count_colaborador_insignias(db, ck, tenant_id),
                    "scope_label": scope_map.get(ck),
                }
            )
            if len(result) >= limit:
                break
        return result
    finally:
        db.close()


def get_metas_departamento(tenant_id="default"):
    db = repo.get_db()
    try:
        start, end = _month_bounds()
        rows = repo.departamentos_meta_rows(db, tenant_id, fecha_desde=start, fecha_hasta=end)
        result = []
        for row in rows:
            dept = row[0] or "Sin departamento"
            inscritos = int(row[1] or 0)
            completados = int(row[2] or 0)
            meta = max(1, inscritos // 2) if inscritos else 1
            result.append(
                {
                    "departamento": dept,
                    "inscritos": inscritos,
                    "completados": completados,
                    "meta": meta,
                    "avance_pct": round((completados / meta) * 100, 1) if meta else 0.0,
                }
            )
        return result
    finally:
        db.close()
