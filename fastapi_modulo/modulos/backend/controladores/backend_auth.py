from __future__ import annotations

from fastapi import APIRouter, Body, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

router = APIRouter()


@router.get("/backend/login", response_class=HTMLResponse)
def backend_login(request: Request):
    from fastapi_modulo import main as core

    login_identity = core._get_login_identity_context()
    return core.templates.TemplateResponse(
        "web_login.html",
        {
            "request": request,
            "title": "Login",
            "login_error": "",
            **login_identity,
        },
    )


@router.get("/backend/404", response_class=HTMLResponse)
def backend_not_found(request: Request):
    from fastapi_modulo import main as core

    return core.templates.TemplateResponse(
        "not_found.html",
        core._not_found_context(request),
    )


@router.post("/backend/login")
def backend_login_submit(
    request: Request,
    usuario: str = Form(""),
    contrasena: str = Form(""),
    codigo_autenticador: str = Form(""),
):
    from urllib.parse import quote
    import re

    from fastapi_modulo import main as core

    login_identity = core._get_login_identity_context()
    if core._is_login_rate_limited(request):
        return core.templates.TemplateResponse(
            "web_login.html",
            {
                "request": request,
                "title": "Login",
                "login_error": "Demasiados intentos. Intenta de nuevo en unos minutos.",
                **login_identity,
            },
            status_code=429,
        )
    username = usuario.strip()
    password = contrasena or ""
    if not username or not password:
        core._register_failed_login_attempt(request)
        return core.templates.TemplateResponse(
            "web_login.html",
            {
                "request": request,
                "title": "Login",
                "login_error": "Datos incorrectos, vuelva a intentarlo",
                **login_identity,
            },
            status_code=401,
        )

    db = core.SessionLocal()
    has_passkey = False
    totp_secret = ""
    try:
        user = core._find_user_by_login(db, username)
        if not user or not core.verify_password(password, user.contrasena or ""):
            core._register_failed_login_attempt(request)
            return core.templates.TemplateResponse(
                "web_login.html",
                {
                    "request": request,
                    "title": "Login",
                    "login_error": "Datos incorrectos, vuelva a intentarlo",
                    **login_identity,
                },
                status_code=401,
            )

        role_name = core._resolve_user_role_name(db, user)
        session_username = core._decrypt_sensitive(user.usuario) or username
        has_passkey = bool(user.backendauthn_credential_id and user.backendauthn_public_key)
        totp_secret = core._get_user_totp_secret(user, role_name)
    finally:
        db.close()

    core._clear_failed_login_attempts(request)
    if role_name == "autoridades":
        code_value = re.sub(r"\s+", "", codigo_autenticador or "")
        if code_value:
            if not totp_secret:
                core._register_failed_login_attempt(request)
                return core.templates.TemplateResponse(
                    "web_login.html",
                    {
                        "request": request,
                        "title": "Login",
                        "login_error": "El código autenticador no está configurado para este usuario.",
                        **login_identity,
                    },
                    status_code=403,
                )
            if not core._verify_totp_code(totp_secret, code_value):
                core._register_failed_login_attempt(request)
                return core.templates.TemplateResponse(
                    "web_login.html",
                    {
                        "request": request,
                        "title": "Login",
                        "login_error": "Código de autenticador inválido.",
                        **login_identity,
                    },
                    status_code=401,
                )
            response = RedirectResponse(url="/inicio", status_code=303)
            core._apply_auth_cookies(response, request, session_username, role_name)
            response.delete_cookie(core.PASSKEY_COOKIE_MFA_GATE)
            return response

        if not has_passkey and not totp_secret:
            return core.templates.TemplateResponse(
                "web_login.html",
                {
                    "request": request,
                    "title": "Login",
                    "login_error": "El rol Autoridades requiere segundo factor (biometría o autenticador) configurado.",
                    **login_identity,
                },
                status_code=403,
            )
        if has_passkey:
            response = RedirectResponse(url=f"/backend/login?mfa=required&usuario={quote(username)}", status_code=303)
            response.set_cookie(
                core.PASSKEY_COOKIE_MFA_GATE,
                core._build_mfa_gate_token(user.id),
                httponly=True,
                samesite="lax",
                secure=core.COOKIE_SECURE,
                max_age=core.PASSKEY_CHALLENGE_TTL_SECONDS,
            )
            return response
        return core.templates.TemplateResponse(
            "web_login.html",
            {
                "request": request,
                "title": "Login",
                "login_error": "Ingresa tu código de autenticador para completar el acceso.",
                **login_identity,
            },
            status_code=401,
        )

    response = RedirectResponse(url="/inicio", status_code=303)
    core._apply_auth_cookies(response, request, session_username, role_name)
    response.delete_cookie(core.PASSKEY_COOKIE_MFA_GATE)
    return response


@router.post("/backend/passkey/register/options")
def passkey_register_options(
    request: Request,
    payload: dict = Body(default={}),
):
    import secrets

    from fastapi_modulo import main as core

    username = str(payload.get("usuario", "")).strip()
    password = str(payload.get("contrasena", ""))
    if not username or not password:
        return JSONResponse({"success": False, "error": "Usuario y contraseña son obligatorios"}, status_code=400)
    if core._is_demo_account(username):
        return JSONResponse(
            {"success": False, "error": "La biometría no está habilitada para el usuario demo"},
            status_code=403,
        )

    db = core.SessionLocal()
    try:
        user = core._find_user_by_login(db, username)
        if not user or not core.verify_password(password, user.contrasena or ""):
            return JSONResponse({"success": False, "error": "Credenciales inválidas"}, status_code=401)
        username_plain = core._decrypt_sensitive(user.usuario) or username
        display_name = (user.full_name or "").strip() or username_plain
        challenge = core._b64url_encode(secrets.token_bytes(32))
        rp_id = core._passkey_rp_id(request)
        origin = core._passkey_origin(request)
        token = core._build_passkey_token("register", user.id, challenge, rp_id, origin)
        options = {
            "challenge": challenge,
            "rp": {"name": "SIPET", "id": rp_id},
            "user": {
                "id": core._b64url_encode(f"user:{user.id}".encode("utf-8")),
                "name": username_plain,
                "displayName": display_name,
            },
            "pubKeyCredParams": [{"type": "public-key", "alg": -7}],
            "timeout": 60000,
            "attestation": "none",
            "authenticatorSelection": {
                "authenticatorAttachment": "platform",
                "residentKey": "preferred",
                "userVerification": "preferred",
            },
        }
        if user.backendauthn_credential_id:
            options["excludeCredentials"] = [
                {
                    "id": user.backendauthn_credential_id,
                    "type": "public-key",
                    "transports": ["internal"],
                }
            ]
    finally:
        db.close()

    response = JSONResponse({"success": True, "options": options})
    response.set_cookie(
        core.PASSKEY_COOKIE_REGISTER,
        token,
        httponly=True,
        samesite="lax",
        secure=core.COOKIE_SECURE,
        max_age=core.PASSKEY_CHALLENGE_TTL_SECONDS,
    )
    return response


@router.post("/backend/passkey/register/verify")
def passkey_register_verify(
    request: Request,
    payload: dict = Body(default={}),
):
    from fastapi_modulo import main as core

    token_data = core._read_passkey_token(request.cookies.get(core.PASSKEY_COOKIE_REGISTER, ""), "register")
    if not token_data:
        return JSONResponse({"success": False, "error": "Solicitud biométrica expirada, inténtalo de nuevo"}, status_code=400)

    credential_id = str(payload.get("id", "")).strip()
    response_payload = payload.get("response") or {}
    if not credential_id or not isinstance(response_payload, dict):
        return JSONResponse({"success": False, "error": "Respuesta biométrica inválida"}, status_code=400)

    client_data = core._parse_client_data(str(response_payload.get("clientDataJSON", "")))
    public_key_b64 = str(response_payload.get("publicKey", "")).strip()
    if not client_data or not public_key_b64:
        return JSONResponse({"success": False, "error": "No se pudo registrar la clave biométrica"}, status_code=400)
    if str(client_data.get("type", "")) != "backendauthn.create":
        return JSONResponse({"success": False, "error": "Tipo de autenticación no válido"}, status_code=400)
    if str(client_data.get("challenge", "")) != token_data["c"]:
        return JSONResponse({"success": False, "error": "Desafío biométrico inválido"}, status_code=400)
    if str(client_data.get("origin", "")).rstrip("/") != token_data["o"].rstrip("/"):
        return JSONResponse({"success": False, "error": "Origen no permitido para biometría"}, status_code=400)

    try:
        public_key_der = core._b64url_decode(public_key_b64)
        core.serialization.load_der_public_key(public_key_der)
    except Exception:
        return JSONResponse({"success": False, "error": "Llave pública biométrica inválida"}, status_code=400)

    db = core.SessionLocal()
    try:
        user = db.query(core.Usuario).filter(core.Usuario.id == token_data["u"]).first()
        if not user:
            return JSONResponse({"success": False, "error": "Usuario no encontrado"}, status_code=404)
        user.backendauthn_credential_id = credential_id
        user.backendauthn_public_key = core._b64url_encode(public_key_der)
        user.backendauthn_sign_count = 0
        db.add(user)
        db.commit()
    except Exception:
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo guardar la biometría"}, status_code=500)
    finally:
        db.close()

    response = JSONResponse({"success": True, "message": "Biometría registrada correctamente"})
    response.delete_cookie(core.PASSKEY_COOKIE_REGISTER)
    return response


@router.post("/backend/passkey/auth/options")
def passkey_auth_options(
    request: Request,
    payload: dict = Body(default={}),
):
    import secrets

    from fastapi_modulo import main as core

    username = str(payload.get("usuario", "")).strip()
    if not username:
        return JSONResponse({"success": False, "error": "Ingresa tu usuario para autenticar con biometría"}, status_code=400)
    if core._is_demo_account(username):
        return JSONResponse(
            {"success": False, "error": "La biometría no está habilitada para el usuario demo"},
            status_code=403,
        )

    db = core.SessionLocal()
    try:
        user = core._find_user_by_login(db, username)
        if not user or not user.backendauthn_credential_id or not user.backendauthn_public_key:
            return JSONResponse({"success": False, "error": "Este usuario no tiene biometría registrada"}, status_code=404)
        role_name = core._resolve_user_role_name(db, user)
        if role_name == "autoridades":
            gate_user_id = core._read_mfa_gate_token(request.cookies.get(core.PASSKEY_COOKIE_MFA_GATE, ""))
            if not gate_user_id or gate_user_id != user.id:
                return JSONResponse(
                    {"success": False, "error": "Primero valida usuario y contraseña para continuar con doble autenticación"},
                    status_code=403,
                )
        challenge = core._b64url_encode(secrets.token_bytes(32))
        rp_id = core._passkey_rp_id(request)
        origin = core._passkey_origin(request)
        token = core._build_passkey_token("auth", user.id, challenge, rp_id, origin)
        options = {
            "challenge": challenge,
            "rpId": rp_id,
            "allowCredentials": [
                {
                    "id": user.backendauthn_credential_id,
                    "type": "public-key",
                    "transports": ["internal"],
                }
            ],
            "timeout": 60000,
            "userVerification": "preferred",
        }
    finally:
        db.close()

    response = JSONResponse({"success": True, "options": options})
    response.set_cookie(
        core.PASSKEY_COOKIE_AUTH,
        token,
        httponly=True,
        samesite="lax",
        secure=core.COOKIE_SECURE,
        max_age=core.PASSKEY_CHALLENGE_TTL_SECONDS,
    )
    return response


@router.post("/backend/passkey/auth/verify")
def passkey_auth_verify(
    request: Request,
    payload: dict = Body(default={}),
):
    import hashlib
    import hmac

    from fastapi_modulo import main as core

    token_data = core._read_passkey_token(request.cookies.get(core.PASSKEY_COOKIE_AUTH, ""), "auth")
    if not token_data:
        return JSONResponse({"success": False, "error": "Solicitud biométrica expirada, inténtalo de nuevo"}, status_code=400)

    credential_id = str(payload.get("id", "")).strip()
    response_payload = payload.get("response") or {}
    if not credential_id or not isinstance(response_payload, dict):
        return JSONResponse({"success": False, "error": "Respuesta biométrica inválida"}, status_code=400)

    client_data_b64 = str(response_payload.get("clientDataJSON", "")).strip()
    auth_data_b64 = str(response_payload.get("authenticatorData", "")).strip()
    signature_b64 = str(response_payload.get("signature", "")).strip()
    if not client_data_b64 or not auth_data_b64 or not signature_b64:
        return JSONResponse({"success": False, "error": "Datos biométricos incompletos"}, status_code=400)

    client_data = core._parse_client_data(client_data_b64)
    if not client_data:
        return JSONResponse({"success": False, "error": "No se pudo leer la respuesta del autenticador"}, status_code=400)
    if str(client_data.get("type", "")) != "backendauthn.get":
        return JSONResponse({"success": False, "error": "Tipo de autenticación no válido"}, status_code=400)
    if str(client_data.get("challenge", "")) != token_data["c"]:
        return JSONResponse({"success": False, "error": "Desafío biométrico inválido"}, status_code=400)
    if str(client_data.get("origin", "")).rstrip("/") != token_data["o"].rstrip("/"):
        return JSONResponse({"success": False, "error": "Origen no permitido para biometría"}, status_code=400)

    try:
        authenticator_data = core._b64url_decode(auth_data_b64)
        signature = core._b64url_decode(signature_b64)
    except ValueError:
        return JSONResponse({"success": False, "error": "Formato biométrico inválido"}, status_code=400)

    if len(authenticator_data) < 37:
        return JSONResponse({"success": False, "error": "AuthenticatorData inválido"}, status_code=400)

    expected_rp_hash = hashlib.sha256(token_data["r"].encode("utf-8")).digest()
    rp_hash = authenticator_data[:32]
    flags = authenticator_data[32]
    sign_count = int.from_bytes(authenticator_data[33:37], "big")
    if not hmac.compare_digest(rp_hash, expected_rp_hash):
        return JSONResponse({"success": False, "error": "RP ID inválido para biometría"}, status_code=400)
    if not (flags & 0x01):
        return JSONResponse({"success": False, "error": "Se requiere presencia del usuario"}, status_code=400)

    client_data_hash = hashlib.sha256(client_data["_raw_bytes"]).digest()
    signed_payload = authenticator_data + client_data_hash

    db = core.SessionLocal()
    try:
        user = db.query(core.Usuario).filter(core.Usuario.id == token_data["u"]).first()
        if not user or not user.backendauthn_credential_id or not user.backendauthn_public_key:
            return JSONResponse({"success": False, "error": "Usuario sin biometría registrada"}, status_code=404)
        if user.backendauthn_credential_id != credential_id:
            return JSONResponse({"success": False, "error": "Credencial biométrica no coincide"}, status_code=401)

        try:
            public_key = core.serialization.load_der_public_key(core._b64url_decode(user.backendauthn_public_key))
        except Exception:
            return JSONResponse({"success": False, "error": "Llave biométrica inválida"}, status_code=400)

        try:
            if isinstance(public_key, core.ec.EllipticCurvePublicKey):
                public_key.verify(signature, signed_payload, core.ec.ECDSA(core.hashes.SHA256()))
            elif isinstance(public_key, core.rsa.RSAPublicKey):
                public_key.verify(signature, signed_payload, core.padding.PKCS1v15(), core.hashes.SHA256())
            else:
                return JSONResponse({"success": False, "error": "Tipo de llave biométrica no soportado"}, status_code=400)
        except core.InvalidSignature:
            return JSONResponse({"success": False, "error": "Firma biométrica inválida"}, status_code=401)

        stored_sign_count = int(user.backendauthn_sign_count or 0)
        if sign_count > 0 and stored_sign_count > 0 and sign_count <= stored_sign_count:
            return JSONResponse({"success": False, "error": "Contador biométrico inválido"}, status_code=401)
        if sign_count > stored_sign_count:
            user.backendauthn_sign_count = sign_count
            db.add(user)
            db.commit()

        role_name = core._resolve_user_role_name(db, user)
        session_username = core._decrypt_sensitive(user.usuario) or core._decrypt_sensitive(user.correo) or f"user-{user.id}"
    finally:
        db.close()

    response = JSONResponse({"success": True, "redirect": "/inicio"})
    core._apply_auth_cookies(response, request, session_username, role_name)
    response.delete_cookie(core.PASSKEY_COOKIE_AUTH)
    response.delete_cookie(core.PASSKEY_COOKIE_MFA_GATE)
    return response


@router.get("/logout")
@router.get("/logout/")
def logout():
    from fastapi_modulo import main as core

    response = RedirectResponse(url="/backend/login", status_code=303)
    response.delete_cookie(core.AUTH_COOKIE_NAME)
    response.delete_cookie("user_role")
    response.delete_cookie("user_name")
    response.delete_cookie("tenant_id")
    response.delete_cookie(core.PASSKEY_COOKIE_AUTH)
    response.delete_cookie(core.PASSKEY_COOKIE_REGISTER)
    response.delete_cookie(core.PASSKEY_COOKIE_MFA_GATE)
    return response
