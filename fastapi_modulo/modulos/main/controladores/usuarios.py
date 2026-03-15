from __future__ import annotations

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func

router = APIRouter()


@router.post("/api/usuarios/registro-seguro")
def crear_usuario_seguro(request: Request, data: dict = Body(...)):
    from fastapi_modulo import main as core

    core.require_admin_or_superadmin(request)
    full_name = (data.get("nombre") or "").strip()
    usuario_login = (data.get("usuario") or "").strip()
    correo = (data.get("correo") or "").strip()
    imagen = (data.get("imagen") or "").strip()
    password = data.get("contrasena") or ""
    rol_nombre = core.normalize_role_name(data.get("rol"))

    if not full_name or not usuario_login or not correo or not password:
        return JSONResponse(
            {"success": False, "error": "nombre, usuario, correo y contrasena son obligatorios"},
            status_code=400,
        )
    if len(password) < 8:
        return JSONResponse(
            {"success": False, "error": "La contraseña debe tener al menos 8 caracteres"},
            status_code=400,
        )

    db = core.SessionLocal()
    try:
        login_hash = core._sensitive_lookup_hash(usuario_login)
        email_hash = core._sensitive_lookup_hash(correo)
        exists_login = db.query(core.Usuario).filter(core.Usuario.usuario_hash == login_hash).first()
        if not exists_login:
            exists_login = db.query(core.Usuario).filter(core.Usuario.usuario == usuario_login).first()
        if exists_login:
            return JSONResponse({"success": False, "error": "El usuario ya existe"}, status_code=409)
        exists_email = db.query(core.Usuario).filter(core.Usuario.correo_hash == email_hash).first()
        if not exists_email:
            exists_email = db.query(core.Usuario).filter(core.Usuario.correo == correo).first()
        if exists_email:
            return JSONResponse({"success": False, "error": "El correo ya existe"}, status_code=409)

        rol_id = None
        if not rol_nombre:
            rol_nombre = "usuario"
        if not core.can_assign_role(request, rol_nombre):
            rol_nombre = "usuario"
        if rol_nombre:
            rol = db.query(core.Rol).filter(core.Rol.nombre == rol_nombre).first()
            if not rol:
                return JSONResponse({"success": False, "error": "Rol no encontrado"}, status_code=404)
            rol_id = rol.id

        nuevo = core.Usuario(
            full_name=full_name,
            usuario=core._encrypt_sensitive(usuario_login),
            usuario_hash=login_hash,
            correo=core._encrypt_sensitive(correo),
            correo_hash=email_hash,
            contrasena=core.hash_password(password),
            rol_id=rol_id,
            imagen=imagen or None,
            role=rol_nombre,
            is_active=True,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return JSONResponse(
            {
                "success": True,
                "data": {
                    "id": nuevo.id,
                    "full_name": nuevo.full_name,
                    "correo": correo,
                    "imagen": nuevo.imagen,
                    "rol_id": nuevo.rol_id,
                },
            }
        )
    finally:
        db.close()


@router.put("/api/usuarios/{user_id}")
def actualizar_usuario_seguro(request: Request, user_id: int, data: dict = Body(...)):
    from fastapi_modulo import main as core

    core.require_admin_or_superadmin(request)
    full_name = (data.get("nombre") or "").strip()
    usuario_login = (data.get("usuario") or "").strip()
    correo = (data.get("correo") or "").strip()
    imagen = (data.get("imagen") or "").strip()
    password = data.get("contrasena") or ""
    rol_nombre = core.normalize_role_name(data.get("rol"))

    if not full_name or not usuario_login or not correo:
        return JSONResponse(
            {"success": False, "error": "nombre, usuario y correo son obligatorios"},
            status_code=400,
        )
    if password and len(password) < 8:
        return JSONResponse(
            {"success": False, "error": "La contraseña debe tener al menos 8 caracteres"},
            status_code=400,
        )

    db = core.SessionLocal()
    try:
        user = db.query(core.Usuario).filter(core.Usuario.id == user_id).first()
        if not user:
            return JSONResponse({"success": False, "error": "Usuario no encontrado"}, status_code=404)

        login_hash = core._sensitive_lookup_hash(usuario_login)
        email_hash = core._sensitive_lookup_hash(correo)
        exists_login = (
            db.query(core.Usuario)
            .filter(core.Usuario.id != user_id, core.Usuario.usuario_hash == login_hash)
            .first()
        )
        if exists_login:
            return JSONResponse({"success": False, "error": "El usuario ya existe"}, status_code=409)
        exists_email = (
            db.query(core.Usuario)
            .filter(core.Usuario.id != user_id, core.Usuario.correo_hash == email_hash)
            .first()
        )
        if exists_email:
            return JSONResponse({"success": False, "error": "El correo ya existe"}, status_code=409)

        if not rol_nombre:
            rol_nombre = "usuario"
        if not core.can_assign_role(request, rol_nombre):
            rol_nombre = "usuario"
        rol = db.query(core.Rol).filter(core.Rol.nombre == rol_nombre).first()
        if not rol:
            return JSONResponse({"success": False, "error": "Rol no encontrado"}, status_code=404)

        user.full_name = full_name
        user.usuario = core._encrypt_sensitive(usuario_login)
        user.usuario_hash = login_hash
        user.correo = core._encrypt_sensitive(correo)
        user.correo_hash = email_hash
        user.rol_id = rol.id
        user.role = rol_nombre
        user.imagen = imagen or None
        if password:
            user.contrasena = core.hash_password(password)
        db.add(user)
        db.commit()
        db.refresh(user)

        return JSONResponse(
            {
                "success": True,
                "data": {
                    "id": user.id,
                    "full_name": user.full_name,
                    "correo": core._decrypt_sensitive(user.correo),
                    "usuario": core._decrypt_sensitive(user.usuario),
                    "imagen": user.imagen,
                    "rol": rol_nombre,
                },
            }
        )
    finally:
        db.close()


@router.get("/api/roles-disponibles")
def listar_roles_disponibles(request: Request):
    from fastapi_modulo import main as core

    core.require_admin_or_superadmin(request)
    allowed = set(core.get_visible_role_names(request))
    db = core.SessionLocal()
    try:
        roles = (
            db.query(core.Rol)
            .filter(core.Rol.nombre.in_(allowed))
            .order_by(core.Rol.id.asc())
            .all()
        )
        data = [
            {
                "id": role.id,
                "nombre": role.nombre,
                "descripcion": role.descripcion,
                "label": role.nombre.replace("_", " ").capitalize(),
            }
            for role in roles
        ]
        return JSONResponse({"success": True, "data": data})
    finally:
        db.close()


@router.get("/api/usuarios")
def listar_usuarios_sanitizados(request: Request):
    from fastapi_modulo import main as core

    core.require_admin_or_superadmin(request)
    db = core.SessionLocal()
    try:
        roles = {r.id: r.nombre for r in db.query(core.Rol).all()}
        usuarios = db.query(core.Usuario).all()

        session_username = (getattr(request.state, "user_name", None) or "").strip()
        session_lookup_hash = core._sensitive_lookup_hash(session_username) if session_username else ""
        session_user = None
        if session_username:
            session_user = (
                db.query(core.Usuario)
                .filter(
                    (core.Usuario.usuario_hash == session_lookup_hash)
                    | (func.lower(core.Usuario.usuario) == session_username.lower())
                )
                .first()
            )

        def resolved_role(user: core.Usuario) -> str:
            if user.rol_id and roles.get(user.rol_id):
                return core.normalize_role_name(roles.get(user.rol_id))
            return core.normalize_role_name(user.role)

        session_role_from_db = resolved_role(session_user) if session_user else ""
        session_is_superadmin = core.is_superadmin(request) or session_role_from_db == "superadministrador"

        data = [
            {
                "id": user.id,
                "full_name": user.full_name,
                "usuario": core._decrypt_sensitive(user.usuario),
                "correo": core._decrypt_sensitive(user.correo),
                "rol": resolved_role(user),
                "imagen": user.imagen,
                "departamento": user.departamento or "",
                "estado": "Activo" if bool(user.is_active) else "Observando",
            }
            for user in usuarios
            if not core.is_hidden_user(request, core._decrypt_sensitive(user.usuario))
            and (session_is_superadmin or resolved_role(user) != "superadministrador")
        ]
        return JSONResponse({"success": True, "data": data})
    finally:
        db.close()
