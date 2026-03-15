from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError

from fastapi_modulo.modulos.capacitacion.modelos.db_models import CapAssetBiblioteca, CapDiapositiva, CapElemento, CapPresentacion, CapPresentacionVersion
from fastapi_modulo.modulos.capacitacion.repositorios import presentaciones_repository as repo
from fastapi_modulo.modulos.capacitacion.servicios.audit_service import registrar_evento

repo.ensure_schema()

DEFAULT_TEMPLATES = [
    {
        "key": "corporativo",
        "nombre": "Corporativo limpio",
        "tema": "azul",
        "descripcion": "Portadas sobrias, bloques de indicadores y llamadas a la accion.",
        "slides": [{"titulo": "Portada", "layout_key": "hero-cover", "bg_color": "#f8fbff"}, {"titulo": "Contenido", "layout_key": "two-columns", "bg_color": "#ffffff"}],
    },
    {
        "key": "cumplimiento",
        "nombre": "Cumplimiento",
        "tema": "granate",
        "descripcion": "Ideal para politicas, normativa y seguimiento institucional.",
        "slides": [{"titulo": "Portada", "layout_key": "hero-centered", "bg_color": "#fff7f7"}, {"titulo": "Checklist", "layout_key": "checklist", "bg_color": "#ffffff"}],
    },
    {
        "key": "onboarding",
        "nombre": "Onboarding",
        "tema": "teal",
        "descripcion": "Ruta de bienvenida con hitos, hotspots y resumenes.",
        "slides": [{"titulo": "Bienvenida", "layout_key": "hero-cover", "bg_color": "#f4fffb"}, {"titulo": "Mapa", "layout_key": "spotlight", "bg_color": "#ffffff"}],
    },
]


def _dt(value):
    if value is None:
        return None
    return value.isoformat() if isinstance(value, datetime) else str(value)


def _loads(value, fallback):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _dumps(value):
    if value is None:
        return None
    return value if isinstance(value, str) else json.dumps(value)


def _version_dict(obj: CapPresentacionVersion):
    return {"id": obj.id, "presentacion_id": obj.presentacion_id, "tipo": obj.tipo, "etiqueta": obj.etiqueta, "actor_key": obj.actor_key, "creado_en": _dt(obj.creado_en)}


def _asset_dict(obj: CapAssetBiblioteca):
    return {
        "id": obj.id,
        "presentacion_id": obj.presentacion_id,
        "nombre": obj.nombre,
        "tipo": obj.tipo,
        "url": obj.url,
        "thumb_url": obj.thumb_url,
        "tags": _loads(obj.tags_json, []),
        "metadata": _loads(obj.metadata_json, {}),
        "creado_por": obj.creado_por,
        "creado_en": _dt(obj.creado_en),
    }


def _el_dict(obj: CapElemento):
    contenido = _loads(obj.contenido_json, {})
    return {
        "id": obj.id,
        "diapositiva_id": obj.diapositiva_id,
        "tipo": obj.tipo,
        "contenido_json": contenido or {},
        "asset_id": obj.asset_id,
        "animation_json": _loads(obj.animation_json, {}),
        "hotspot_key": obj.hotspot_key,
        "pos_x": obj.pos_x,
        "pos_y": obj.pos_y,
        "width": obj.width,
        "height": obj.height,
        "z_index": obj.z_index,
    }


def _diap_dict(obj: CapDiapositiva, include_elementos: bool = False):
    data = {
        "id": obj.id,
        "presentacion_id": obj.presentacion_id,
        "orden": obj.orden,
        "titulo": obj.titulo,
        "layout_key": obj.layout_key,
        "transition_key": obj.transition_key,
        "animation_json": _loads(obj.animation_json, {}),
        "responsive_json": _loads(obj.responsive_json, {}),
        "bg_color": obj.bg_color or "#ffffff",
        "bg_image_url": obj.bg_image_url,
        "notas": obj.notas,
        "creado_en": _dt(obj.creado_en),
    }
    if include_elementos:
        data["elementos"] = [_el_dict(item) for item in sorted(obj.elementos, key=lambda item: item.z_index)]
    return data


def _pres_dict(obj: CapPresentacion, include_diapositivas: bool = False):
    data = {
        "id": obj.id,
        "titulo": obj.titulo,
        "descripcion": obj.descripcion,
        "autor_key": obj.autor_key,
        "template_key": obj.template_key,
        "theme_key": obj.theme_key,
        "responsive_mode": obj.responsive_mode,
        "autosave": _loads(obj.autosave_json, {}),
        "estado": obj.estado,
        "curso_id": obj.curso_id,
        "miniatura_url": obj.miniatura_url,
        "creado_por": obj.creado_por,
        "actualizado_por": obj.actualizado_por,
        "publicado_por": obj.publicado_por,
        "publicado_en": _dt(obj.publicado_en),
        "num_diapositivas": len(obj.diapositivas) if obj.diapositivas else 0,
        "creado_en": _dt(obj.creado_en),
        "actualizado_en": _dt(obj.actualizado_en),
    }
    if include_diapositivas:
        data["diapositivas"] = [_diap_dict(item, True) for item in sorted(obj.diapositivas, key=lambda item: item.orden)]
    return data


def _touch_presentacion(db, pres_id, actor_key=None):
    presentacion = repo.get_presentacion(db, pres_id)
    if not presentacion:
        return None
    presentacion.actualizado_en = datetime.utcnow()
    if actor_key:
        presentacion.actualizado_por = actor_key
    db.flush()
    return presentacion


def _snapshot_payload(presentacion):
    return {
        "presentacion": _pres_dict(presentacion),
        "diapositivas": [_diap_dict(item, True) for item in sorted(presentacion.diapositivas, key=lambda row: row.orden)],
    }


def _create_snapshot(db, presentacion, actor_key=None, tipo="snapshot", etiqueta=None):
    payload = _snapshot_payload(presentacion)
    return repo.create_version(
        db,
        {
            "tenant_id": presentacion.tenant_id,
            "presentacion_id": presentacion.id,
            "tipo": tipo,
            "etiqueta": etiqueta or tipo,
            "contenido_json": json.dumps(payload),
            "actor_key": actor_key,
            "creado_en": datetime.utcnow(),
        },
    )


def get_templates():
    return DEFAULT_TEMPLATES


def list_presentaciones(autor_key=None, estado=None, curso_id=None, tenant_id=None):
    db = repo.get_db()
    try:
        return [_pres_dict(item) for item in repo.list_presentaciones(db, autor_key, estado, curso_id)]
    finally:
        db.close()


def get_presentacion(pres_id, tenant_id=None):
    db = repo.get_db()
    try:
        obj = repo.get_presentacion(db, pres_id)
        return _pres_dict(obj) if obj else None
    finally:
        db.close()


def create_presentacion(data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        actor = actor_key or data.get("autor_key")
        template_key = data.get("template_key")
        template = next((item for item in DEFAULT_TEMPLATES if item["key"] == template_key), None)
        payload = {
            "titulo": data.get("titulo", "Nueva presentación"),
            "descripcion": data.get("descripcion"),
            "autor_key": data.get("autor_key"),
            "template_key": template_key,
            "theme_key": data.get("theme_key") or (template.get("tema") if template else None),
            "responsive_mode": data.get("responsive_mode", "desktop"),
            "estado": data.get("estado", "borrador"),
            "curso_id": data.get("curso_id") or None,
            "creado_por": actor,
            "actualizado_por": actor,
            "creado_en": datetime.utcnow(),
            "actualizado_en": datetime.utcnow(),
        }
        if tenant_id:
            payload["tenant_id"] = tenant_id
        if str(payload["estado"]) == "publicado":
            payload["publicado_por"] = actor
            payload["publicado_en"] = datetime.utcnow()
        obj = repo.create_presentacion(db, payload)
        slides_seed = template.get("slides") if template else [{"titulo": "Diapositiva 1", "layout_key": "blank", "bg_color": "#ffffff"}]
        for idx, slide in enumerate(slides_seed):
            repo.create_diapositiva(
                db,
                {
                    "presentacion_id": obj.id,
                    "orden": idx,
                    "titulo": slide.get("titulo", f"Diapositiva {idx + 1}"),
                    "layout_key": slide.get("layout_key", "blank"),
                    "transition_key": slide.get("transition_key", "fade"),
                    "responsive_json": json.dumps({"desktop": {"scale": 1}, "tablet": {"scale": 0.9}, "mobile": {"scale": 0.75}}),
                    "bg_color": slide.get("bg_color", "#ffffff"),
                    "creado_en": datetime.utcnow(),
                    "tenant_id": obj.tenant_id,
                },
            )
        _create_snapshot(db, obj, actor_key=actor, tipo="created", etiqueta="Creacion inicial")
        registrar_evento(db, "presentacion", obj.id, "created", actor_key=actor, actor_nombre=actor_name, tenant_id=obj.tenant_id, detalle={"titulo": obj.titulo, "estado": str(obj.estado), "template_key": template_key})
        if str(obj.estado) == "publicado":
            registrar_evento(db, "presentacion", obj.id, "published", actor_key=actor, actor_nombre=actor_name, tenant_id=obj.tenant_id, detalle={"estado": str(obj.estado)})
        db.commit()
        db.refresh(obj)
        return _pres_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_presentacion(pres_id, data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        current = repo.get_presentacion(db, pres_id)
        if not current:
            return None
        prev_estado = str(current.estado)
        allowed = {key: value for key, value in data.items() if key in {"titulo", "descripcion", "estado", "curso_id", "miniatura_url", "template_key", "theme_key", "responsive_mode"}}
        if "autosave" in data:
            allowed["autosave_json"] = _dumps(data.get("autosave", {}))
        allowed["actualizado_en"] = datetime.utcnow()
        if actor_key:
            allowed["actualizado_por"] = actor_key
        next_estado = str(allowed.get("estado") or prev_estado)
        if next_estado == "publicado" and prev_estado != "publicado":
            allowed["publicado_por"] = actor_key
            allowed["publicado_en"] = datetime.utcnow()
        obj = repo.update_presentacion(db, pres_id, allowed)
        if not obj:
            return None
        registrar_evento(db, "presentacion", obj.id, "updated", actor_key=actor_key, actor_nombre=actor_name, tenant_id=obj.tenant_id, detalle={"estado_anterior": prev_estado, "estado_nuevo": str(obj.estado)})
        if prev_estado != "publicado" and str(obj.estado) == "publicado":
            registrar_evento(db, "presentacion", obj.id, "published", actor_key=actor_key, actor_nombre=actor_name, tenant_id=obj.tenant_id, detalle={"estado_anterior": prev_estado, "estado_nuevo": str(obj.estado)})
        db.commit()
        db.refresh(obj)
        return _pres_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_presentacion(pres_id, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        obj = repo.get_presentacion(db, pres_id)
        if obj:
            registrar_evento(db, "presentacion", obj.id, "deleted", actor_key=actor_key, actor_nombre=actor_name, tenant_id=obj.tenant_id, detalle={"titulo": obj.titulo})
        ok = repo.delete_presentacion(db, pres_id)
        if not ok:
            return False
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_diapositivas(pres_id, tenant_id=None):
    db = repo.get_db()
    try:
        return [_diap_dict(item, True) for item in repo.list_diapositivas(db, pres_id)]
    finally:
        db.close()


def create_diapositiva(pres_id, data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        orden = len(repo.list_diapositivas(db, pres_id))
        presentacion = repo.get_presentacion(db, pres_id)
        obj = repo.create_diapositiva(
            db,
            {
                "presentacion_id": pres_id,
                "orden": orden,
                "titulo": data.get("titulo", f"Diapositiva {orden + 1}"),
                "layout_key": data.get("layout_key", "blank"),
                "transition_key": data.get("transition_key", "fade"),
                "animation_json": _dumps(data.get("animation_json", {})),
                "responsive_json": _dumps(data.get("responsive_json", {"desktop": {}, "tablet": {}, "mobile": {}})),
                "bg_color": data.get("bg_color", "#ffffff"),
                "bg_image_url": data.get("bg_image_url"),
                "notas": data.get("notas"),
                "creado_en": datetime.utcnow(),
                "tenant_id": tenant_id or (presentacion.tenant_id if presentacion else "default"),
            },
        )
        touched = _touch_presentacion(db, pres_id, actor_key)
        if touched:
            registrar_evento(db, "presentacion", touched.id, "slide_created", actor_key=actor_key, actor_nombre=actor_name, tenant_id=touched.tenant_id, detalle={"diapositiva_id": obj.id, "titulo": obj.titulo, "layout_key": obj.layout_key})
        db.commit()
        db.refresh(obj)
        return _diap_dict(obj, True)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def update_diapositiva(diap_id, data, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        obj = repo.get_diapositiva(db, diap_id)
        if not obj:
            return None
        updates = {
            "titulo": data.get("titulo", obj.titulo),
            "layout_key": data.get("layout_key", obj.layout_key),
            "transition_key": data.get("transition_key", obj.transition_key),
            "bg_color": data.get("bg_color", obj.bg_color),
            "bg_image_url": data.get("bg_image_url", obj.bg_image_url),
            "notas": data.get("notas", obj.notas),
        }
        for key, value in updates.items():
            setattr(obj, key, value)
        if "animation_json" in data:
            obj.animation_json = _dumps(data.get("animation_json", {}))
        if "responsive_json" in data:
            obj.responsive_json = _dumps(data.get("responsive_json", {}))
        touched = _touch_presentacion(db, obj.presentacion_id, actor_key)
        if touched:
            registrar_evento(db, "presentacion", touched.id, "slide_updated", actor_key=actor_key, actor_nombre=actor_name, tenant_id=touched.tenant_id, detalle={"diapositiva_id": obj.id, "titulo": obj.titulo})
        db.commit()
        db.refresh(obj)
        return _diap_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_diapositiva(diap_id, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        obj = repo.get_diapositiva(db, diap_id)
        if not obj:
            return False
        pres_id = obj.presentacion_id
        pres = repo.get_presentacion(db, pres_id)
        if pres:
            registrar_evento(db, "presentacion", pres.id, "slide_deleted", actor_key=actor_key, actor_nombre=actor_name, tenant_id=pres.tenant_id, detalle={"diapositiva_id": obj.id, "titulo": obj.titulo})
        repo.delete_diapositiva(db, diap_id)
        db.flush()
        for index, slide in enumerate(repo.list_diapositivas(db, pres_id)):
            slide.orden = index
        _touch_presentacion(db, pres_id, actor_key)
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def reordenar_diapositivas(pres_id, orden_ids, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        for index, diap_id in enumerate(orden_ids):
            slide = repo.get_diapositiva(db, diap_id)
            if slide and slide.presentacion_id == pres_id:
                slide.orden = index
        touched = _touch_presentacion(db, pres_id, actor_key)
        if touched:
            registrar_evento(db, "presentacion", touched.id, "slides_reordered", actor_key=actor_key, actor_nombre=actor_name, tenant_id=touched.tenant_id, detalle={"orden_ids": orden_ids})
        db.commit()
        return True
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def duplicate_diapositiva(diap_id, tenant_id=None, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        orig = repo.get_diapositiva(db, diap_id)
        if not orig:
            return None
        new_orden = orig.orden + 1
        for slide in repo.list_diapositivas(db, orig.presentacion_id):
            if slide.orden >= new_orden:
                slide.orden += 1
        new_diap = repo.create_diapositiva(
            db,
            {
                "presentacion_id": orig.presentacion_id,
                "orden": new_orden,
                "titulo": (orig.titulo or "Diapositiva") + " (copia)",
                "layout_key": orig.layout_key,
                "transition_key": orig.transition_key,
                "animation_json": orig.animation_json,
                "responsive_json": orig.responsive_json,
                "bg_color": orig.bg_color,
                "bg_image_url": orig.bg_image_url,
                "notas": orig.notas,
                "creado_en": datetime.utcnow(),
                "tenant_id": orig.tenant_id,
            },
        )
        for element in orig.elementos:
            repo.create_elemento(
                db,
                {
                    "diapositiva_id": new_diap.id,
                    "tipo": element.tipo,
                    "contenido_json": element.contenido_json,
                    "asset_id": element.asset_id,
                    "animation_json": element.animation_json,
                    "hotspot_key": element.hotspot_key,
                    "pos_x": element.pos_x,
                    "pos_y": element.pos_y,
                    "width": element.width,
                    "height": element.height,
                    "z_index": element.z_index,
                    "creado_en": datetime.utcnow(),
                    "tenant_id": orig.tenant_id,
                },
            )
        touched = _touch_presentacion(db, orig.presentacion_id, actor_key)
        if touched:
            registrar_evento(db, "presentacion", touched.id, "slide_duplicated", actor_key=actor_key, actor_nombre=actor_name, tenant_id=touched.tenant_id, detalle={"origen_id": orig.id, "copia_id": new_diap.id})
        db.commit()
        db.refresh(new_diap)
        return _diap_dict(new_diap, True)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_elementos(diap_id, tenant_id=None):
    db = repo.get_db()
    try:
        return [_el_dict(item) for item in repo.list_elementos(db, diap_id)]
    finally:
        db.close()


def save_elementos(diap_id, elementos, tenant_id=None, actor_key=None, actor_name=None, autosave=False):
    db = repo.get_db()
    try:
        diap = repo.get_diapositiva(db, diap_id)
        if not diap:
            raise ValueError("La diapositiva no existe")
        repo.delete_elementos(db, diap_id)
        nuevos = []
        for data in elementos:
            nuevos.append(
                repo.create_elemento(
                    db,
                    {
                        "diapositiva_id": diap_id,
                        "tipo": data.get("tipo", "texto"),
                        "contenido_json": _dumps(data.get("contenido_json", {})),
                        "asset_id": data.get("asset_id"),
                        "animation_json": _dumps(data.get("animation_json", {})),
                        "hotspot_key": data.get("hotspot_key"),
                        "pos_x": float(data.get("pos_x", 10)),
                        "pos_y": float(data.get("pos_y", 10)),
                        "width": float(data.get("width", 30)),
                        "height": float(data.get("height", 20)),
                        "z_index": int(data.get("z_index", 1)),
                        "creado_en": datetime.utcnow(),
                        "tenant_id": diap.tenant_id,
                    },
                )
            )
        touched = _touch_presentacion(db, diap.presentacion_id, actor_key)
        if touched:
            if autosave:
                touched.autosave_json = json.dumps({"diapositiva_id": diap.id, "at": _dt(datetime.utcnow())})
                _create_snapshot(db, touched, actor_key=actor_key, tipo="autosave", etiqueta="Auto guardado")
            registrar_evento(db, "presentacion", touched.id, "elements_saved", actor_key=actor_key, actor_nombre=actor_name, tenant_id=touched.tenant_id, detalle={"diapositiva_id": diap.id, "total_elementos": len(nuevos), "autosave": autosave})
        db.commit()
        for item in nuevos:
            db.refresh(item)
        return [_el_dict(item) for item in nuevos]
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def duplicate_elemento(diap_id, element_id, actor_key=None, actor_name=None):
    db = repo.get_db()
    try:
        diap = repo.get_diapositiva(db, diap_id)
        if not diap:
            return None
        origen = next((item for item in diap.elementos if item.id == element_id), None)
        if not origen:
            return None
        nuevo = repo.create_elemento(
            db,
            {
                "diapositiva_id": diap_id,
                "tipo": origen.tipo,
                "contenido_json": origen.contenido_json,
                "asset_id": origen.asset_id,
                "animation_json": origen.animation_json,
                "hotspot_key": (origen.hotspot_key or "hotspot") + "-" + uuid.uuid4().hex[:6],
                "pos_x": origen.pos_x + 4,
                "pos_y": origen.pos_y + 4,
                "width": origen.width,
                "height": origen.height,
                "z_index": max([item.z_index for item in diap.elementos] + [0]) + 1,
                "creado_en": datetime.utcnow(),
                "tenant_id": diap.tenant_id,
            },
        )
        touched = _touch_presentacion(db, diap.presentacion_id, actor_key)
        if touched:
            registrar_evento(db, "presentacion", touched.id, "block_duplicated", actor_key=actor_key, actor_nombre=actor_name, tenant_id=touched.tenant_id, detalle={"diapositiva_id": diap.id, "elemento_id": element_id, "copia_id": nuevo.id})
        db.commit()
        db.refresh(nuevo)
        return _el_dict(nuevo)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def create_version_snapshot(pres_id, actor_key=None, etiqueta=None):
    db = repo.get_db()
    try:
        pres = repo.get_presentacion(db, pres_id)
        if not pres:
            return None
        obj = _create_snapshot(db, pres, actor_key=actor_key, tipo="manual", etiqueta=etiqueta or "Version manual")
        registrar_evento(db, "presentacion", pres.id, "version_created", actor_key=actor_key, tenant_id=pres.tenant_id, detalle={"version_id": obj.id})
        db.commit()
        db.refresh(obj)
        return _version_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_versiones(pres_id, limit=20):
    db = repo.get_db()
    try:
        return [_version_dict(item) for item in repo.list_versions(db, pres_id, limit=limit)]
    finally:
        db.close()


def list_assets(pres_id=None, asset_type=None):
    db = repo.get_db()
    try:
        return [_asset_dict(item) for item in repo.list_assets(db, pres_id, asset_type)]
    finally:
        db.close()


def create_asset(data, pres_id=None, tenant_id=None, actor_key=None):
    db = repo.get_db()
    try:
        obj = repo.create_asset(
            db,
            {
                "tenant_id": tenant_id or "default",
                "presentacion_id": pres_id,
                "nombre": data.get("nombre") or "Asset",
                "tipo": data.get("tipo") or "imagen",
                "url": data.get("url"),
                "thumb_url": data.get("thumb_url"),
                "tags_json": _dumps(data.get("tags", [])),
                "metadata_json": _dumps(data.get("metadata", {})),
                "creado_por": actor_key,
                "creado_en": datetime.utcnow(),
            },
        )
        db.commit()
        db.refresh(obj)
        return _asset_dict(obj)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()
