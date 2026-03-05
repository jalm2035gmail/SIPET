import os
import uuid
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Request, Body, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from sqlalchemy.exc import IntegrityError
from fastapi_modulo.db import SessionLocal

router = APIRouter()
COLAB_UPLOAD_DIR = Path("fastapi_modulo/uploads/colaboradores")
_APP_ENV = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()
_DEFAULT_SIPET_DATA_DIR = (os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data")).strip()
_RUNTIME_STORE_DIR = (os.environ.get("RUNTIME_STORE_DIR") or os.path.join(_DEFAULT_SIPET_DATA_DIR, "runtime_store", _APP_ENV)).strip()
COLAB_META_PATH = Path(
    os.environ.get("COLAB_META_PATH") or os.path.join(_RUNTIME_STORE_DIR, "colaboradores_meta.json")
)


def _colab_sort_key(row: Dict[str, Any]) -> tuple[str, str]:
    name = (row.get("nombre") or "").strip().lower()
    user = (row.get("usuario") or "").strip().lower()
    return (name or user, user)


def _load_colab_meta() -> Dict[str, Dict[str, Any]]:
    try:
        if not COLAB_META_PATH.exists():
            return {}
        raw = json.loads(COLAB_META_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _save_colab_meta(meta: Dict[str, Dict[str, Any]]) -> None:
    COLAB_META_PATH.parent.mkdir(parents=True, exist_ok=True)
    COLAB_META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _normalize_poa_access_level(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return "todas_tareas" if raw == "todas_tareas" else "mis_tareas"


def _is_admin_role(role_name: str) -> bool:
    role = (role_name or "").strip().lower()
    if role == "admin":
        role = "administrador"
    if role == "super_admin":
        role = "superadministrador"
    if role == "superadministrdor":
        role = "superadministrador"
    return role in {"superadministrador", "administrador"}


def _allowed_role_assignments(viewer_role: str) -> set[str]:
    role = (viewer_role or "").strip().lower()
    if role == "admin":
        role = "administrador"
    if role == "super_admin":
        role = "superadministrador"
    if role == "superadministrdor":
        role = "superadministrador"
    if role == "superadministrador":
        return {"superadministrador", "administrador", "usuario", "autoridades", "departamento"}
    if role == "administrador":
        return {"administrador", "usuario", "autoridades", "departamento"}
    return set()

EMPLEADOS_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo",
    "templates",
    "modulos",
    "empleados",
    "empleados.html",
)


@router.get("/api/colaboradores", response_class=JSONResponse)
def api_listar_colaboradores(request: Request):
    # Import diferido para evitar importación circular con fastapi_modulo.main.
    from fastapi_modulo.main import Usuario, Rol, _decrypt_sensitive, normalize_role_name

    db = SessionLocal()
    try:
        meta = _load_colab_meta()
        rows = db.query(Usuario).all()
        names_by_id = {u.id: (u.nombre or "").strip() for u in rows}
        roles_by_id = {role.id: normalize_role_name(role.nombre) for role in db.query(Rol).all()}
        viewer_role = normalize_role_name((getattr(request.state, "user_role", None) or "").strip().lower())
        assignable_roles = sorted(_allowed_role_assignments(viewer_role))
        data: List[Dict[str, Any]] = [
            {
                "id": u.id,
                "nombre": u.nombre or "",
                "usuario": (_decrypt_sensitive(u.usuario) or "").strip(),
                "correo": (_decrypt_sensitive(u.correo) or "").strip(),
                "departamento": u.departamento or "",
                "imagen": u.imagen or "",
                "jefe_inmediato_id": getattr(u, "jefe_inmediato_id", None),
                "jefe": (
                    names_by_id.get(getattr(u, "jefe_inmediato_id", None))
                    or u.jefe
                    or ""
                ),
                "puesto": u.puesto or "",
                "rol": (
                    roles_by_id.get(u.rol_id)
                    or normalize_role_name(getattr(u, "role", "") or "usuario")
                    or "usuario"
                ),
                "colaborador": bool(meta.get(str(u.id), {}).get("colaborador", False)),
                "menu_blocks": meta.get(str(u.id), {}).get("menu_blocks", []),
                "poa_access_level": _normalize_poa_access_level(meta.get(str(u.id), {}).get("poa_access_level", "mis_tareas")),
                "app_access": meta.get(str(u.id), {}).get("app_access", []),
                "web_roles": meta.get(str(u.id), {}).get("web_roles", []),
                "eficiencia": meta.get(str(u.id), {}).get("eficiencia", None),
                "cv_contacto": meta.get(str(u.id), {}).get("cv_contacto", {}),
                "cv_perfil_profesional": meta.get(str(u.id), {}).get("cv_perfil_profesional", ""),
                "cv_experiencia": meta.get(str(u.id), {}).get("cv_experiencia", []),
                "cv_educacion": meta.get(str(u.id), {}).get("cv_educacion", []),
                "cv_habilidades": meta.get(str(u.id), {}).get("cv_habilidades", {"tecnicas": [], "blandas": []}),
                "cv_idiomas": meta.get(str(u.id), {}).get("cv_idiomas", []),
                "cv_formacion": meta.get(str(u.id), {}).get("cv_formacion", []),
                "cv_logros": meta.get(str(u.id), {}).get("cv_logros", []),
                "cv_publicaciones": meta.get(str(u.id), {}).get("cv_publicaciones", []),
                "cv_voluntariado": meta.get(str(u.id), {}).get("cv_voluntariado", []),
                "cv_info_adicional": meta.get(str(u.id), {}).get("cv_info_adicional", {}),
                "estado": "Activo" if getattr(u, "is_active", True) else "Inactivo",
            }
            for u in rows
        ]
        can_view_all = _is_admin_role(viewer_role)
        viewer_username = (getattr(request.state, "user_name", None) or "").strip().lower()
        if viewer_role == "superadministrador":
            pass
        elif viewer_role == "administrador":
            data = [row for row in data if (row.get("rol") or "").strip().lower() != "superadministrador"]
        else:
            data = [row for row in data if (row.get("usuario") or "").strip().lower() == viewer_username]
            for row in data:
                if (row.get("rol") or "").strip().lower() == "superadministrador":
                    row["rol"] = ""
        data = sorted(data, key=_colab_sort_key)
        return {
            "success": True,
            "data": data,
            "viewer_role": viewer_role,
            "can_view_all": can_view_all,
            "can_manage_access": can_view_all,
            "assignable_roles": assignable_roles,
        }
    finally:
        db.close()


@router.get("/api/colaboradores/organigrama", response_class=JSONResponse)
def api_organigrama_colaboradores(request: Request):
    # Import diferido para evitar importación circular con fastapi_modulo.main.
    from fastapi_modulo.main import Usuario, Rol, _decrypt_sensitive, normalize_role_name

    db = SessionLocal()
    try:
        meta = _load_colab_meta()
        rows = db.query(Usuario).all()
        names_by_id = {u.id: (u.nombre or "").strip() for u in rows}
        roles_by_id = {role.id: normalize_role_name(role.nombre) for role in db.query(Rol).all()}
        all_rows: List[Dict[str, Any]] = [
            {
                "id": u.id,
                "nombre": u.nombre or "",
                "usuario": (_decrypt_sensitive(u.usuario) or "").strip(),
                "correo": (_decrypt_sensitive(u.correo) or "").strip(),
                "departamento": u.departamento or "",
                "imagen": u.imagen or "",
                "jefe_inmediato_id": getattr(u, "jefe_inmediato_id", None),
                "jefe": (
                    names_by_id.get(getattr(u, "jefe_inmediato_id", None))
                    or u.jefe
                    or ""
                ),
                "puesto": u.puesto or "",
                "rol": (
                    roles_by_id.get(u.rol_id)
                    or normalize_role_name(getattr(u, "role", "") or "usuario")
                    or "usuario"
                ),
                "colaborador": bool(meta.get(str(u.id), {}).get("colaborador", False)),
                "estado": "Activo" if getattr(u, "is_active", True) else "Inactivo",
            }
            for u in rows
        ]
        # Solo nodos marcados como colaborador entran al organigrama.
        all_rows = [row for row in all_rows if bool(row.get("colaborador"))]

        viewer_username = (getattr(request.state, "user_name", None) or "").strip().lower()
        viewer_role = normalize_role_name((getattr(request.state, "user_role", None) or "").strip().lower())
        can_view_all = _is_admin_role(viewer_role)
        if viewer_role == "administrador":
            all_rows = [row for row in all_rows if (row.get("rol") or "").strip().lower() != "superadministrador"]
        if can_view_all:
            return {"success": True, "data": all_rows, "viewer_role": viewer_role, "can_view_all": True}

        # Usuario regular: solo él + subordinados hacia abajo (sin jefes hacia arriba).
        me = None
        for row in all_rows:
            if (row.get("usuario") or "").strip().lower() == viewer_username:
                me = row
                break
        if not me:
            return {"success": True, "data": [], "viewer_role": viewer_role, "can_view_all": False}

        visible_ids = {int(me["id"])}
        queue = [me]
        while queue:
            current = queue.pop(0)
            current_name = (current.get("nombre") or "").strip().lower()
            current_user = (current.get("usuario") or "").strip().lower()
            for row in all_rows:
                if int(row["id"]) in visible_ids:
                    continue
                boss_id = row.get("jefe_inmediato_id")
                boss = (row.get("jefe") or "").strip().lower()
                if (boss_id and int(boss_id) == int(current["id"])) or (boss and boss in {current_name, current_user}):
                    visible_ids.add(int(row["id"]))
                    queue.append(row)

        filtered = [row for row in all_rows if int(row["id"]) in visible_ids]
        return {"success": True, "data": filtered, "viewer_role": viewer_role, "can_view_all": False}
    finally:
        db.close()


@router.post("/api/colaboradores", response_class=JSONResponse)
def api_guardar_colaborador(request: Request, data: dict = Body(...)):
    # Import diferido para evitar importación circular con fastapi_modulo.main.
    from fastapi_modulo.main import (
        Usuario,
        Rol,
        _decrypt_sensitive,
        _encrypt_sensitive,
        _sensitive_lookup_hash,
        hash_password,
        normalize_role_name,
        require_admin_or_superadmin,
    )
    require_admin_or_superadmin(request)
    viewer_role = normalize_role_name((getattr(request.state, "user_role", None) or "").strip().lower())
    allowed_assignments = _allowed_role_assignments(viewer_role)
    nombre = (data.get("nombre") or "").strip()
    incoming_id = data.get("id")
    try:
        incoming_id = int(incoming_id) if incoming_id not in (None, "") else None
    except Exception:
        incoming_id = None
    usuario_login = (data.get("usuario") or "").strip()
    correo = (data.get("correo") or "").strip()
    password = str(data.get("contrasena") or "")
    departamento = (data.get("departamento") or "").strip()
    puesto = (data.get("puesto") or "").strip()
    jefe_inmediato_id = data.get("jefe_inmediato_id")
    try:
        jefe_inmediato_id = int(jefe_inmediato_id) if jefe_inmediato_id not in (None, "") else None
    except Exception:
        jefe_inmediato_id = None
    celular = (data.get("celular") or "").strip()
    nivel_organizacional = (data.get("nivel_organizacional") or "").strip()
    imagen = (data.get("imagen") or "").strip()
    raw_eficiencia = data.get("eficiencia")
    eficiencia: Optional[int] = None
    if raw_eficiencia is not None and str(raw_eficiencia).strip() != "":
        try:
            eficiencia = max(0, min(100, int(float(str(raw_eficiencia).strip()))))
        except (ValueError, TypeError):
            eficiencia = None
    colaborador = bool(data.get("colaborador"))
    requested_role = normalize_role_name((data.get("rol") or "").strip() or "usuario")
    if requested_role not in allowed_assignments:
        requested_role = "usuario"
    raw_menu_blocks = data.get("menu_blocks")
    menu_blocks: List[str] = []
    if isinstance(raw_menu_blocks, list):
        menu_blocks = [str(item).strip() for item in raw_menu_blocks if str(item).strip()]
    elif isinstance(raw_menu_blocks, str) and raw_menu_blocks.strip():
        menu_blocks = [raw_menu_blocks.strip()]
    menu_blocks = sorted(set(menu_blocks))
    poa_access_level = _normalize_poa_access_level(data.get("poa_access_level"))
    raw_app_access = data.get("app_access")
    app_access: List[str] = []
    _VALID_APPS = {'BSC','Organización','Estrategia y táctica','Datos financieros','Control y seguimiento','KPIs','Reportes','Empresa'}
    if isinstance(raw_app_access, list):
        app_access = [str(a).strip() for a in raw_app_access if str(a).strip() in _VALID_APPS]
    raw_web_roles = data.get("web_roles")
    web_roles: List[str] = []
    _VALID_WEB_ROLES = {'editor', 'designer'}
    if isinstance(raw_web_roles, list):
        web_roles = [str(r).strip() for r in raw_web_roles if str(r).strip() in _VALID_WEB_ROLES]
    raw_cv_contacto = data.get("cv_contacto") or {}
    cv_contacto: dict = {}
    if isinstance(raw_cv_contacto, dict):
        for _k in ("nombre_completo", "telefono", "correo_electronico", "direccion", "linkedin", "portfolio"):
            cv_contacto[_k] = str(raw_cv_contacto.get(_k) or "").strip()
    cv_perfil_profesional: str = str(data.get("cv_perfil_profesional") or "").strip()
    raw_cv_experiencia = data.get("cv_experiencia") or []
    cv_experiencia: list = []
    if isinstance(raw_cv_experiencia, list):
        _exp_fields = ("cargo", "empresa", "inicio_mes", "inicio_anio", "fin_mes", "fin_anio", "logros")
        for _exp in raw_cv_experiencia:
            if isinstance(_exp, dict):
                entry = {f: str(_exp.get(f) or "").strip() for f in _exp_fields}
                entry["actual"] = bool(_exp.get("actual", False))
                cv_experiencia.append(entry)
    raw_cv_educacion = data.get("cv_educacion") or []
    cv_educacion: list = []
    if isinstance(raw_cv_educacion, list):
        _edu_fields = ("titulo", "institucion", "inicio_mes", "inicio_anio", "fin_mes", "fin_anio")
        for _edu in raw_cv_educacion:
            if isinstance(_edu, dict):
                entry = {f: str(_edu.get(f) or "").strip() for f in _edu_fields}
                entry["actual"] = bool(_edu.get("actual", False))
                cv_educacion.append(entry)
    raw_cv_habilidades = data.get("cv_habilidades") or {}
    cv_habilidades: dict = {"tecnicas": [], "blandas": []}
    if isinstance(raw_cv_habilidades, dict):
        for _cat in ("tecnicas", "blandas"):
            raw_list = raw_cv_habilidades.get(_cat) or []
            if isinstance(raw_list, list):
                for _s in raw_list:
                    if isinstance(_s, dict):
                        cv_habilidades[_cat].append({
                            "nombre": str(_s.get("nombre") or "").strip(),
                            "nivel":  str(_s.get("nivel")  or "").strip(),
                        })
    raw_cv_idiomas = data.get("cv_idiomas") or []
    cv_idiomas: list = []
    if isinstance(raw_cv_idiomas, list):
        for _id in raw_cv_idiomas:
            if isinstance(_id, dict):
                cv_idiomas.append({
                    "nombre": str(_id.get("nombre") or "").strip(),
                    "nivel":  str(_id.get("nivel")  or "").strip(),
                })
    raw_cv_formacion = data.get("cv_formacion") or []
    cv_formacion: list = []
    if isinstance(raw_cv_formacion, list):
        _forma_fields = ("nombre", "entidad", "mes", "anio", "descripcion")
        for _fr in raw_cv_formacion:
            if isinstance(_fr, dict):
                cv_formacion.append({f: str(_fr.get(f) or "").strip() for f in _forma_fields})
    raw_cv_logros = data.get("cv_logros") or []
    cv_logros: list = []
    if isinstance(raw_cv_logros, list):
        _logro_fields = ("titulo", "entidad", "mes", "anio", "descripcion")
        for _lg in raw_cv_logros:
            if isinstance(_lg, dict):
                cv_logros.append({f: str(_lg.get(f) or "").strip() for f in _logro_fields})
    raw_cv_publicaciones = data.get("cv_publicaciones") or []
    cv_publicaciones: list = []
    if isinstance(raw_cv_publicaciones, list):
        _pub_fields = ("titulo", "tipo", "autores", "publicado_en", "mes", "anio", "url")
        for _pb in raw_cv_publicaciones:
            if isinstance(_pb, dict):
                cv_publicaciones.append({f: str(_pb.get(f) or "").strip() for f in _pub_fields})
    raw_cv_voluntariado = data.get("cv_voluntariado") or []
    cv_voluntariado: list = []
    if isinstance(raw_cv_voluntariado, list):
        for _vl in raw_cv_voluntariado:
            if isinstance(_vl, dict):
                entry = {f: str(_vl.get(f) or "").strip() for f in ("organizacion", "rol", "inicio_mes", "inicio_anio", "fin_mes", "fin_anio", "descripcion")}
                entry["actual"] = bool(_vl.get("actual", False))
                cv_voluntariado.append(entry)
    raw_cv_info_adicional = data.get("cv_info_adicional") or {}
    cv_info_adicional: dict = {}
    if isinstance(raw_cv_info_adicional, dict):
        cv_info_adicional = {
            "carnet_conducir":         bool(raw_cv_info_adicional.get("carnet_conducir", False)),
            "tipo_carnet":             str(raw_cv_info_adicional.get("tipo_carnet") or "").strip(),
            "vehiculo_propio":         bool(raw_cv_info_adicional.get("vehiculo_propio", False)),
            "disponibilidad_viaje":    str(raw_cv_info_adicional.get("disponibilidad_viaje") or "").strip(),
            "disponibilidad_traslado": str(raw_cv_info_adicional.get("disponibilidad_traslado") or "").strip(),
            "notas":                   str(raw_cv_info_adicional.get("notas") or "").strip(),
        }

    identidad_mision: str = str(data.get("identidad_mision") or "").strip()
    identidad_vision: str = str(data.get("identidad_vision") or "").strip()

    if not nombre or not usuario_login:
        return JSONResponse(
            {"success": False, "error": "Nombre y usuario son obligatorios"},
            status_code=400,
        )
    if incoming_id is None and not password:
        return JSONResponse(
            {"success": False, "error": "La contraseña es obligatoria para crear colaborador"},
            status_code=400,
        )
    if password and len(password) < 8:
        return JSONResponse(
            {"success": False, "error": "La contraseña debe tener al menos 8 caracteres"},
            status_code=400,
        )

    db = SessionLocal()
    try:
        from sqlalchemy import func
        from fastapi_modulo.main import ensure_default_roles
        ensure_default_roles()
        target_role = db.query(Rol).filter(Rol.nombre == requested_role).first()
        if not target_role:
            target_role = (
                db.query(Rol)
                .filter(func.lower(Rol.nombre) == requested_role.lower())
                .first()
            )
        if not target_role:
            target_role = (
                db.query(Rol)
                .filter(func.lower(Rol.nombre) == "usuario")
                .first()
            )
        if not target_role:
            return JSONResponse({"success": False, "error": "Rol no encontrado"}, status_code=404)
        rol_id = target_role.id
        user_hash = _sensitive_lookup_hash(usuario_login)
        email_hash = _sensitive_lookup_hash(correo) if correo else None
        jefe_inmediato_nombre = ""
        if jefe_inmediato_id and incoming_id and int(jefe_inmediato_id) == int(incoming_id):
            return JSONResponse(
                {"success": False, "error": "El jefe inmediato no puede ser el mismo colaborador"},
                status_code=400,
            )
        if jefe_inmediato_id:
            jefe_exists = db.query(Usuario).filter(Usuario.id == jefe_inmediato_id).first()
            if not jefe_exists:
                return JSONResponse(
                    {"success": False, "error": "El jefe inmediato seleccionado no existe"},
                    status_code=400,
                )
            jefe_inmediato_nombre = (jefe_exists.nombre or "").strip()

        existing = None
        if incoming_id:
            existing = db.query(Usuario).filter(Usuario.id == incoming_id).first()
        # Duplicate check: for new users check all records; for edits exclude the current user.
        _dup_user_q = db.query(Usuario).filter(Usuario.usuario_hash == user_hash)
        if incoming_id:
            _dup_user_q = _dup_user_q.filter(Usuario.id != incoming_id)
        duplicate_by_username = _dup_user_q.first()
        if duplicate_by_username:
            return JSONResponse(
                {"success": False, "error": "No se pudo guardar: el usuario ya existe."},
                status_code=409,
            )
        if email_hash:
            _dup_email_q = db.query(Usuario).filter(Usuario.correo_hash == email_hash)
            if incoming_id:
                _dup_email_q = _dup_email_q.filter(Usuario.id != incoming_id)
            duplicate_by_email = _dup_email_q.first()
            if duplicate_by_email:
                return JSONResponse(
                    {"success": False, "error": "No se pudo guardar: el correo ya existe."},
                    status_code=409,
                )

        if existing:
            existing.nombre = nombre
            existing.usuario = _encrypt_sensitive(usuario_login)
            existing.usuario_hash = user_hash
            existing.correo = _encrypt_sensitive(correo) if correo else None
            existing.correo_hash = email_hash
            existing.departamento = departamento
            existing.puesto = puesto
            existing.jefe_inmediato_id = jefe_inmediato_id
            existing.jefe = jefe_inmediato_nombre
            existing.celular = celular
            existing.coach = nivel_organizacional
            existing.imagen = imagen or None
            existing.role = requested_role
            existing.rol_id = rol_id
            existing.is_active = True
            if password:
                existing.contrasena = hash_password(password)
            db.add(existing)
            db.commit()
            db.refresh(existing)
            meta = _load_colab_meta()
            meta[str(existing.id)] = {
                "colaborador": colaborador,
                "menu_blocks": menu_blocks,
                "poa_access_level": poa_access_level,
                "app_access": app_access,
                "web_roles": web_roles,
                "eficiencia": eficiencia,
                "cv_contacto": cv_contacto,
                "cv_perfil_profesional": cv_perfil_profesional,
                "cv_experiencia": cv_experiencia,
                "cv_educacion": cv_educacion,
                "cv_habilidades": cv_habilidades,
                "cv_idiomas": cv_idiomas,
                "cv_formacion": cv_formacion,
                "cv_logros": cv_logros,
                "cv_publicaciones": cv_publicaciones,
                "cv_voluntariado": cv_voluntariado,
                "cv_info_adicional": cv_info_adicional,
                "identidad_mision": identidad_mision,
                "identidad_vision": identidad_vision,
            }
            _save_colab_meta(meta)
            return {
                "success": True,
                "message": "Colaborador actualizado correctamente",
                "data": {
                    "id": existing.id,
                    "nombre": existing.nombre or "",
                    "usuario": _decrypt_sensitive(existing.usuario) or "",
                    "correo": _decrypt_sensitive(existing.correo) or "",
                    "departamento": existing.departamento or "",
                    "puesto": existing.puesto or "",
                    "jefe_inmediato_id": existing.jefe_inmediato_id,
                    "celular": existing.celular or "",
                    "nivel_organizacional": existing.coach or "",
                    "imagen": existing.imagen or "",
                    "rol": requested_role,
                    "colaborador": colaborador,
                    "menu_blocks": menu_blocks,
                    "poa_access_level": poa_access_level,
                    "app_access": app_access,
                    "web_roles": web_roles,
                    "eficiencia": eficiencia,
                    "cv_contacto": cv_contacto,
                    "cv_perfil_profesional": cv_perfil_profesional,
                    "cv_experiencia": cv_experiencia,
                    "cv_educacion": cv_educacion,
                    "cv_habilidades": cv_habilidades,
                    "cv_idiomas": cv_idiomas,
                    "cv_formacion": cv_formacion,
                    "cv_logros": cv_logros,
                    "cv_publicaciones": cv_publicaciones,
                    "cv_voluntariado": cv_voluntariado,
                    "cv_info_adicional": cv_info_adicional,
                    "identidad_mision": identidad_mision,
                    "identidad_vision": identidad_vision,
                    "estado": "Activo" if bool(getattr(existing, "is_active", True)) else "Inactivo",
                },
            }

        nuevo = Usuario(
            nombre=nombre,
            usuario=_encrypt_sensitive(usuario_login),
            usuario_hash=user_hash,
            correo=_encrypt_sensitive(correo) if correo else None,
            correo_hash=email_hash,
            contrasena=hash_password(password),
            departamento=departamento,
            puesto=puesto,
            jefe=jefe_inmediato_nombre,
            jefe_inmediato_id=jefe_inmediato_id,
            celular=celular,
            coach=nivel_organizacional,
            imagen=imagen or None,
            role=requested_role,
            rol_id=rol_id,
            is_active=True,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        meta = _load_colab_meta()
        meta[str(nuevo.id)] = {
            "colaborador": colaborador,
            "menu_blocks": menu_blocks,
            "poa_access_level": poa_access_level,
            "app_access": app_access,
            "web_roles": web_roles,
            "eficiencia": eficiencia,
            "cv_contacto": cv_contacto,
            "cv_perfil_profesional": cv_perfil_profesional,
            "cv_experiencia": cv_experiencia,
            "cv_educacion": cv_educacion,
            "cv_habilidades": cv_habilidades,
            "cv_idiomas": cv_idiomas,
            "cv_formacion": cv_formacion,
            "cv_logros": cv_logros,
            "cv_publicaciones": cv_publicaciones,
            "cv_voluntariado": cv_voluntariado,
            "cv_info_adicional": cv_info_adicional,
            "identidad_mision": identidad_mision,
            "identidad_vision": identidad_vision,
        }
        _save_colab_meta(meta)
        return {
            "success": True,
            "message": "Colaborador creado correctamente",
            "data": {
                "id": nuevo.id,
                "nombre": nuevo.nombre or "",
                "usuario": _decrypt_sensitive(nuevo.usuario) or "",
                "correo": _decrypt_sensitive(nuevo.correo) or "",
                "departamento": nuevo.departamento or "",
                "puesto": nuevo.puesto or "",
                "jefe_inmediato_id": nuevo.jefe_inmediato_id,
                "celular": nuevo.celular or "",
                "nivel_organizacional": nuevo.coach or "",
                "imagen": nuevo.imagen or "",
                "rol": requested_role,
                "colaborador": colaborador,
                "menu_blocks": menu_blocks,
                "poa_access_level": poa_access_level,
                "app_access": app_access,
                "web_roles": web_roles,
                "eficiencia": eficiencia,
                "cv_contacto": cv_contacto,
                "cv_perfil_profesional": cv_perfil_profesional,
                "cv_experiencia": cv_experiencia,
                "cv_educacion": cv_educacion,
                "cv_habilidades": cv_habilidades,
                "cv_idiomas": cv_idiomas,
                "cv_formacion": cv_formacion,
                "cv_logros": cv_logros,
                "cv_publicaciones": cv_publicaciones,
                "cv_voluntariado": cv_voluntariado,
                "cv_info_adicional": cv_info_adicional,
                "identidad_mision": identidad_mision,
                "identidad_vision": identidad_vision,
                "estado": "Activo",
            },
        }
    except IntegrityError:
        db.rollback()
        return JSONResponse(
            {
                "success": False,
                "error": "No se pudo guardar: el usuario o correo ya existe.",
            },
            status_code=409,
        )
    except Exception as exc:
        db.rollback()
        return JSONResponse(
            {
                "success": False,
                "error": f"No se pudo guardar: {exc}",
            },
            status_code=500,
        )
    finally:
        db.close()


@router.delete("/api/colaboradores/{colaborador_id}", response_class=JSONResponse)
def api_eliminar_colaborador(request: Request, colaborador_id: int):
    from fastapi_modulo.main import (
        Usuario,
        Rol,
        normalize_role_name,
        require_admin_or_superadmin,
        is_superadmin,
    )

    require_admin_or_superadmin(request)
    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.id == colaborador_id).first()
        if not user:
            return JSONResponse({"success": False, "error": "Colaborador no encontrado"}, status_code=404)
        roles_by_id = {role.id: normalize_role_name(role.nombre) for role in db.query(Rol).all()}
        target_role = (
            roles_by_id.get(getattr(user, "rol_id", None))
            or normalize_role_name(getattr(user, "role", "") or "usuario")
            or "usuario"
        )
        if target_role == "superadministrador" and not is_superadmin(request):
            return JSONResponse(
                {"success": False, "error": "Solo superadministrador puede eliminar superadministradores"},
                status_code=403,
            )
        db.delete(user)
        db.commit()
        meta = _load_colab_meta()
        key = str(colaborador_id)
        if key in meta:
            del meta[key]
            _save_colab_meta(meta)
        return {"success": True}
    finally:
        db.close()


@router.post("/api/colaboradores/foto", response_class=JSONResponse)
async def api_subir_foto_colaborador(request: Request, file: UploadFile = File(...)):
    from fastapi_modulo.main import require_admin_or_superadmin
    from fastapi_modulo.image_utils import optimize_image

    require_admin_or_superadmin(request)
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
        ext = ".png"
    COLAB_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="La imagen supera 5MB")
    # Optimizar: redimensionar a 300×300 máx y convertir a WebP
    optimized, final_ext = optimize_image(content, ext, profile="avatar")
    filename = f"colab_{uuid.uuid4().hex}{final_ext}"
    target = COLAB_UPLOAD_DIR / filename
    target.write_bytes(optimized)
    return {"success": True, "url": f"/colaboradores/uploads/{filename}"}


@router.get("/colaboradores/uploads/{filename}")
def api_ver_foto_colaborador(filename: str):
    safe_name = Path(filename).name
    target = COLAB_UPLOAD_DIR / safe_name
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(target)


def _load_empleados_template() -> str:
    try:
        with open(EMPLEADOS_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return """
        <section id="usuario-panel" class="usuario-panel">
            <div id="usuario-view"></div>
        </section>
        """


def _render_empleados_page(
    request: Request,
    title: str = "Usuarios",
    description: str = "Gestiona usuarios, roles y permisos desde la misma pantalla",
) -> HTMLResponse:
    from fastapi_modulo.main import render_backend_page

    return render_backend_page(
        request,
        title=title,
        description=description,
        content=_load_empleados_template(),
        hide_floating_actions=True,
        view_buttons=[
            {"label": "Form", "icon": "/templates/icon/formulario.svg", "view": "form"},
            {"label": "Lista", "icon": "/templates/icon/list.svg", "view": "list", "active": True},
            {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
            {"label": "Organigrama", "icon": "/icon/organigrama.svg", "view": "organigrama"},
        ],
        floating_actions_screen="none",
    )


@router.get("/usuarios", response_class=HTMLResponse)
@router.get("/usuarios-sistema", response_class=HTMLResponse)
def usuarios_page(request: Request):
    return _render_empleados_page(request)


@router.get("/inicio/colaboradores", response_class=HTMLResponse)
def inicio_colaboradores_page(request: Request):
    return _render_empleados_page(
        request,
        title="Colaboradores",
        description="Gestiona colaboradores, roles y permisos desde la misma pantalla",
    )


# ── Habilidades catalog store ─────────────────────────────────────────────────
_HAB_CATALOG_PATH = Path(
    os.environ.get("HAB_CATALOG_PATH")
    or os.path.join(_RUNTIME_STORE_DIR, "habilidades_catalog.json")
)

_HAB_DEFAULTS: dict = {
    "comunicacion_interpersonales": [
        "Comunicación asertiva (verbal y escrita)",
        "Escucha activa",
        "Empatía",
        "Negociación",
        "Oratoria / Hablar en público",
        "Persuasión",
        "Redacción profesional",
        "Manejo de conversaciones difíciles",
        "Trabajo en equipo",
        "Colaboración interdepartamental",
    ],
    "liderazgo_gestion": [
        "Toma de decisiones",
        "Gestión de conflictos",
        "Mentoría / Coaching",
        "Inteligencia emocional",
        "Capacidad para motivar a otros",
        "Delegación efectiva",
        "Pensamiento estratégico",
        "Visión de negocio",
    ],
    "liderazgo_equipos": [
        "Toma de decisiones",
        "Gestión de conflictos",
        "Mentoría / Coaching",
        "Inteligencia emocional",
        "Capacidad para motivar a otros",
        "Delegación efectiva",
        "Pensamiento estratégico",
        "Visión de negocio",
    ],
    "resolucion_pensamiento": [
        "Pensamiento crítico",
        "Creatividad e innovación",
        "Adaptabilidad / Flexibilidad al cambio",
        "Gestión de crisis",
        "Orientación a resultados",
        "Negociación bajo presión",
        "Capacidad de análisis",
        "Atención al detalle",
    ],
    "organizacion_autogestion": [
        "Gestión del tiempo",
        "Organización y planificación",
        "Autonomía / Iniciativa propia",
        "Responsabilidad",
        "Puntualidad",
        "Resiliencia (capacidad de superar adversidades)",
        "Proactividad",
        "Multitarea (manejo de múltiples tareas)",
        "Aprendizaje rápido (adaptabilidad cognitiva)",
    ],
    "informatica_tecnologia_general": [
        "Word: Procesador de textos avanzado",
        "Excel: Tablas dinámicas, Macros, BuscarV, Power Query",
        "PowerPoint: Creación de presentaciones ejecutivas",
        "Outlook: Gestión de correo y calendario",
        "Google Workspace: Gmail, Drive, Docs, Sheets, Slides, Meet",
        "Navegación y búsqueda: Investigación avanzada en internet",
        "Redes sociales corporativas: LinkedIn, Twitter (X) para marca personal",
    ],
    "tecnologias_informacion_it": [
        "Lenguajes de programación: Python, Java, JavaScript, C++, C#, PHP, Ruby, SQL",
        "Desarrollo web: HTML5, CSS3, React, Angular, Vue.js, Node.js",
        "Bases de datos: MySQL, PostgreSQL, MongoDB, Oracle",
        "Ciberseguridad: Ethical Hacking, Firewalls, Gestión de vulnerabilidades",
        "Cloud Computing: AWS (Amazon), Microsoft Azure, Google Cloud",
        "Sistemas operativos: Windows Server, Linux (Ubuntu, CentOS), macOS",
        "Administración de redes: TCP/IP, DNS, DHCP, VPN, Cisco",
        "DevOps: Docker, Kubernetes, Jenkins",
    ],
    "diseno_multimedia": [
        "Diseño gráfico: Adobe Photoshop, Illustrator, InDesign, Canva",
        "Edición de video: Adobe Premiere, Final Cut Pro, DaVinci Resolve",
        "Edición de audio / Podcast: Audacity, Adobe Audition",
        "Modelado 3D / Animación: Blender, AutoCAD, Maya, 3ds Max",
        "UX/UI: Figma, Sketch, Adobe XD, diseño de experiencia de usuario",
    ],
    "marketing_ventas_comunicacion": [
        "Marketing Digital: SEO, SEM (Google Ads), Email Marketing",
        "Analítica Web: Google Analytics, Google Search Console",
        "CRM: Salesforce, HubSpot, Zoho, Microsoft Dynamics",
        "Gestión de Redes Sociales: Hootsuite, Buffer, Meta Business Suite",
        "Copywriting: Redacción persuasiva para ventas y anuncios",
        "Atención al cliente: Gestión de quejas, fidelización, CRM de soporte",
    ],
    "finanzas_contabilidad_administracion": [
        "Software Contable: SAP, QuickBooks, Alegra, Kactus, Contasis (en Ecuador)",
        "Análisis financiero: Elaboración de estados financieros, balances",
        "Presupuestos y forecasting",
        "Declaración de impuestos: Conocimiento del SRI (Ecuador) y facturación electrónica",
        "Gestión de nóminas (Role de pagos)",
        "Auditoría interna",
    ],
    "logistica_produccion_operaciones": [
        "Gestión de inventarios: Just in Time, EOQ",
        "Manejo de ERP: SAP MM, Odoo",
        "Cadena de suministro (Supply Chain)",
        "Comercio exterior: Documentación de aduanas, Incoterms",
        "Normas de calidad: ISO 9001, Six Sigma, Lean Manufacturing",
    ],
    "idiomas_duros": [
        "Inglés (Nivel A1 a C2)",
        "Portugués (clave para negocios en Sudamérica)",
        "Francés, Alemán, Mandarín, etc.",
        "Lengua de señas (LSEC)",
    ],
    "sector_salud": [
        "Soporte Vital Básico (RCP)",
        "Manejo de historias clínicas (digitales)",
        "Conocimiento en farmacología",
        "Instrumentación quirúrgica",
        "Bioseguridad",
    ],
    "sector_legal": [
        "Redacción de contratos",
        "Litigio oral",
        "Investigación jurídica",
        "Derecho laboral / tributario",
    ],
    "habilidades_manuales_tecnicas": [
        "Manejo de maquinaria pesada",
        "Soldadura (MIG, TIG, arco eléctrico)",
        "Electricidad domiciliaria/industrial",
        "Carpintería o ebanistería",
        "Manejo de herramientas de construcción",
        "Carnet de conducir profesional (Tipo E, D, etc.)",
    ],
}


def _load_hab_catalog() -> dict:
    try:
        if _HAB_CATALOG_PATH.exists():
            data = json.loads(_HAB_CATALOG_PATH.read_text(encoding="utf-8"))
            # Merge: keep defaults for missing keys
            catalog = dict(_HAB_DEFAULTS)
            catalog.update({k: v for k, v in data.items() if k in catalog})
            return catalog
    except Exception:
        pass
    return dict({k: list(v) for k, v in _HAB_DEFAULTS.items()})


def _save_hab_catalog(catalog: dict) -> None:
    _HAB_CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _HAB_CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/api/habilidades-catalog", response_class=JSONResponse)
def habilidades_catalog_get(request: Request):
    return JSONResponse(_load_hab_catalog())


@router.post("/api/habilidades-catalog", response_class=JSONResponse)
async def habilidades_catalog_save(request: Request):
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError("body must be object")
        catalog = _load_hab_catalog()
        for key, items in body.items():
            if key in catalog and isinstance(items, list):
                catalog[key] = [str(i).strip() for i in items if str(i).strip()]
        _save_hab_catalog(catalog)
        return JSONResponse({"success": True, "catalog": catalog})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)


@router.get("/inicio/colaboradores/habilidades", response_class=HTMLResponse)
def colaboradores_habilidades_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    content = """
<style>
/* ── Layout ── */
.hab-accordion { display: flex; flex-direction: column; gap: 14px; max-width: 860px; }
/* ── Level-1 blocks ── */
.hab-block {
    border: 1px solid color-mix(in srgb, var(--button-bg,#0f172a) 16%, #ffffff 84%);
    border-radius: 14px; overflow: hidden; background: #fff;
}
.hab-block > summary {
    display: flex; align-items: center; justify-content: space-between;
    padding: 18px 22px; cursor: pointer; list-style: none; user-select: none;
    font-weight: 600; font-size: 1.05rem; color: var(--sidebar-bottom,#0f172a);
    background: color-mix(in srgb, var(--button-bg,#0f172a) 4%, #ffffff 96%);
    transition: background 0.15s;
}
.hab-block > summary::-webkit-details-marker { display: none; }
.hab-block > summary:hover { background: color-mix(in srgb, var(--button-bg,#0f172a) 8%, #ffffff 92%); }
.hab-block-title { display: flex; align-items: center; gap: 8px; flex: 1; font-size:1.05rem; }
.hab-block-icon { font-size: 1.3rem; }
.hab-block-caret { font-size:0.8rem; color:color-mix(in srgb,var(--button-bg,#0f172a) 35%,#ffffff 65%); transition:transform 0.2s; }
.hab-block[open] > summary .hab-block-caret { transform: rotate(180deg); }
.hab-block-body { padding: 20px; border-top: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%); }
/* ── Level-2 sub-blocks ── */
.hab-sub-accordion { display: flex; flex-direction: column; gap: 8px; }
.hab-sub-block {
    border: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 11%,#ffffff 89%);
    border-radius: 10px; overflow: hidden;
}
.hab-sub-block > summary {
    display: flex; align-items: center; justify-content: space-between;
    padding: 11px 16px; cursor: pointer; list-style: none; user-select: none;
    font-weight: 600; font-size: 0.9rem; color: var(--sidebar-bottom,#0f172a);
    background: color-mix(in srgb,var(--button-bg,#0f172a) 5%,#ffffff 95%);
    transition: background 0.15s;
}
.hab-sub-block > summary::-webkit-details-marker { display: none; }
.hab-sub-block > summary:hover { background: color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%); }
.hab-sub-title { display: flex; align-items: center; gap: 7px; flex: 1; }
.hab-sub-emoji { font-size: 1rem; }
.hab-sub-caret { font-size:0.72rem; color:color-mix(in srgb,var(--button-bg,#0f172a) 30%,#ffffff 70%); transition:transform 0.2s; }
.hab-sub-block[open] > summary .hab-sub-caret { transform: rotate(180deg); }
.hab-sub-body { padding: 14px 16px; border-top: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 8%,#ffffff 92%); }
/* ── Items list ── */
.hab-items { list-style: none; margin: 0 0 10px; padding: 0; display: flex; flex-direction: column; gap: 5px; }
.hab-item {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 10px;
    border: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%);
    border-radius: 8px;
    background: color-mix(in srgb,var(--button-bg,#0f172a) 3%,#ffffff 97%);
    font-size: 0.875rem; color: var(--sidebar-bottom,#0f172a);
}
.hab-item-text { flex: 1; }
.hab-item-edit, .hab-item-del {
    flex: 0 0 auto; border: none; background: none; cursor: pointer;
    padding: 3px 5px; border-radius: 5px; font-size: 0.8rem; line-height: 1;
    transition: background 0.12s;
}
.hab-item-edit { color: color-mix(in srgb,var(--button-bg,#0f172a) 45%,#ffffff 55%); }
.hab-item-edit:hover { background: color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%); }
.hab-item-del { color: #ef4444; }
.hab-item-del:hover { background: #fee2e2; }
/* ── Item edit inline ── */
.hab-item.editing .hab-item-text { display: none; }
.hab-item.editing .hab-item-input { display: block; }
.hab-item.editing .hab-item-edit { display: none; }
.hab-item.editing .hab-item-save { display: inline-block; }
.hab-item-input {
    display: none; flex: 1; border: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 20%,#ffffff 80%);
    border-radius: 6px; padding: 4px 8px; font-size: 0.875rem;
    background: var(--field-color,#fff); color: var(--navbar-text,#0f172a);
    outline: none; font-family: inherit;
}
.hab-item-save {
    display: none; flex: 0 0 auto; border: none;
    background: color-mix(in srgb,var(--button-bg,#0f172a) 90%,#ffffff 10%);
    color: #fff; border-radius: 6px; padding: 4px 10px; font-size: 0.8rem; cursor: pointer;
}
/* ── Add row ── */
.hab-add-row { display: flex; gap: 7px; margin-top: 4px; }
.hab-add-input {
    flex: 1; border: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 20%,#ffffff 80%);
    border-radius: 8px; padding: 7px 10px; font-size: 0.875rem;
    background: var(--field-color,#fff); color: var(--navbar-text,#0f172a);
    outline: none; font-family: inherit;
}
.hab-add-input:focus { border-color: color-mix(in srgb,var(--button-bg,#0f172a) 40%,#ffffff 60%); }
.hab-add-btn {
    flex: 0 0 auto; border: none; border-radius: 8px; padding: 7px 14px;
    background: color-mix(in srgb,var(--button-bg,#0f172a) 90%,#ffffff 10%);
    color: #fff; font-size: 0.875rem; cursor: pointer; white-space: nowrap;
    transition: opacity 0.15s;
}
.hab-add-btn:hover { opacity: 0.85; }
/* ── Save bar ── */
.hab-save-bar {
    display: none; position: sticky; bottom: 14px;
    background: color-mix(in srgb,var(--button-bg,#0f172a) 96%,#ffffff 4%);
    color: #fff; border-radius: 12px; padding: 12px 20px;
    font-size: 0.9rem; align-items: center; justify-content: space-between; gap: 12px;
    box-shadow: 0 4px 20px #0003; z-index: 50; margin-top: 18px;
}
.hab-save-bar.visible { display: flex; }
.hab-save-btn {
    border: none; border-radius: 8px; padding: 8px 22px;
    background: #22c55e; color: #fff; font-size: 0.9rem; font-weight: 600;
    cursor: pointer; white-space: nowrap; transition: opacity 0.15s;
}
.hab-save-btn:hover { opacity: 0.85; }
.hab-save-msg { font-size: 0.82rem; opacity: 0.75; }
</style>

<div class="hab-accordion" id="hab-root">
    <!-- HABILIDADES BLANDAS -->
    <details class="hab-block" open>
        <summary>
            <span class="hab-block-title"><span class="hab-block-icon">&#129309;</span> Habilidades blandas</span>
            <span class="hab-block-caret">&#9660;</span>
        </summary>
        <div class="hab-block-body">
            <div class="hab-sub-accordion">
                <details class="hab-sub-block" open>
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#128483;</span> Comunicaci&oacute;n e Interpersonales</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="comunicacion_interpersonales"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#127775;</span> Liderazgo y Gesti&oacute;n</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="liderazgo_gestion"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#128101;</span> Liderazgo de equipos</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="liderazgo_equipos"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#129504;</span> Resoluci&oacute;n y Pensamiento</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="resolucion_pensamiento"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#128197;</span> Organizaci&oacute;n y Autogesti&oacute;n</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="organizacion_autogestion"></div>
                </details>
            </div>
        </div>
    </details>
    <!-- HABILIDADES DURAS -->
    <details class="hab-block" open>
        <summary>
            <span class="hab-block-title"><span class="hab-block-icon">&#9881;&#65039;</span> Habilidades duras</span>
            <span class="hab-block-caret">&#9660;</span>
        </summary>
        <div class="hab-block-body">
            <div class="hab-sub-accordion">
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#128187;</span> Inform&aacute;tica y Tecnolog&iacute;a (Generales)</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="informatica_tecnologia_general"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#128225;</span> Tecnolog&iacute;as de la Informaci&oacute;n (IT)</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="tecnologias_informacion_it"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#127912;</span> Dise&ntilde;o y Multimedia</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="diseno_multimedia"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#128200;</span> Marketing, Ventas y Comunicaci&oacute;n</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="marketing_ventas_comunicacion"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#128181;</span> Finanzas, Contabilidad y Administraci&oacute;n</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="finanzas_contabilidad_administracion"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#128666;</span> Log&iacute;stica, Producci&oacute;n y Operaciones</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="logistica_produccion_operaciones"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#127760;</span> Idiomas</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="idiomas_duros"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#129657;</span> Sector Salud</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="sector_salud"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#9878;&#65039;</span> Sector Legal</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="sector_legal"></div>
                </details>
                <details class="hab-sub-block">
                    <summary><span class="hab-sub-title"><span class="hab-sub-emoji">&#128296;</span> Habilidades Manuales o T&eacute;cnicas Espec&iacute;ficas</span><span class="hab-sub-caret">&#9660;</span></summary>
                    <div class="hab-sub-body" data-cat="habilidades_manuales_tecnicas"></div>
                </details>
            </div>
        </div>
    </details>
</div>

<!-- Save bar -->
<div class="hab-save-bar" id="hab-save-bar">
    <span class="hab-save-msg">Tienes cambios sin guardar</span>
    <button class="hab-save-btn" id="hab-save-btn">Guardar cambios</button>
</div>

<script>
(function() {
    var catalog = {};
    var dirty = false;

    function markDirty() {
        dirty = true;
        document.getElementById('hab-save-bar').classList.add('visible');
    }

    function renderCat(cat) {
        var items = catalog[cat] || [];
        var body = document.querySelector('[data-cat="' + cat + '"]');
        if (!body) return;
        var ul = document.createElement('ul');
        ul.className = 'hab-items';
        items.forEach(function(text, idx) {
            var li = document.createElement('li');
            li.className = 'hab-item';
            li.dataset.idx = idx;
            li.innerHTML =
                '<span class="hab-item-text">' + _esc(text) + '</span>' +
                '<input class="hab-item-input" value="' + _esc(text) + '" />' +
                '<button class="hab-item-save" title="Guardar">&#10003;</button>' +
                '<button class="hab-item-edit" title="Editar">&#9998;</button>' +
                '<button class="hab-item-del" title="Eliminar">&times;</button>';
            // edit
            li.querySelector('.hab-item-edit').addEventListener('click', function() {
                li.classList.add('editing');
                li.querySelector('.hab-item-input').focus();
            });
            // save inline
            li.querySelector('.hab-item-save').addEventListener('click', function() {
                var val = li.querySelector('.hab-item-input').value.trim();
                if (!val) return;
                catalog[cat][idx] = val;
                li.classList.remove('editing');
                li.querySelector('.hab-item-text').textContent = val;
                li.querySelector('.hab-item-input').value = val;
                markDirty();
            });
            li.querySelector('.hab-item-input').addEventListener('keydown', function(e) {
                if (e.key === 'Enter') li.querySelector('.hab-item-save').click();
                if (e.key === 'Escape') { li.classList.remove('editing'); }
            });
            // delete
            li.querySelector('.hab-item-del').addEventListener('click', function() {
                catalog[cat].splice(idx, 1);
                markDirty();
                renderCat(cat);
            });
            ul.appendChild(li);
        });
        // add row
        var addRow = document.createElement('div');
        addRow.className = 'hab-add-row';
        addRow.innerHTML = '<input class="hab-add-input" placeholder="Nueva habilidad..." /><button class="hab-add-btn">+ Agregar</button>';
        var inp = addRow.querySelector('.hab-add-input');
        var btn = addRow.querySelector('.hab-add-btn');
        function doAdd() {
            var v = inp.value.trim();
            if (!v) return;
            if (!catalog[cat]) catalog[cat] = [];
            catalog[cat].push(v);
            markDirty();
            renderCat(cat);
            // re-focus new input
            var newInp = document.querySelector('[data-cat="' + cat + '"] .hab-add-input');
            if (newInp) newInp.focus();
        }
        btn.addEventListener('click', doAdd);
        inp.addEventListener('keydown', function(e) { if (e.key === 'Enter') doAdd(); });
        body.innerHTML = '';
        body.appendChild(ul);
        body.appendChild(addRow);
    }

    function _esc(s) {
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // load
    fetch('/api/habilidades-catalog')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            catalog = data;
            Object.keys(catalog).forEach(renderCat);
        });

    // save
    document.getElementById('hab-save-btn').addEventListener('click', function() {
        fetch('/api/habilidades-catalog', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(catalog)
        })
        .then(function(r) { return r.json(); })
        .then(function(res) {
            if (res.success) {
                dirty = false;
                document.getElementById('hab-save-bar').classList.remove('visible');
            }
        });
    });
})();
</script>
"""
    return render_backend_page(
        request,
        title="Habilidades",
        description="Módulo de habilidades de colaboradores",
        content=content,
        hide_floating_actions=True,
        floating_actions_screen="none",
    )
