from __future__ import annotations

import csv
import json
import secrets
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
import pandas as pd
from pydantic import ValidationError
from sqlalchemy import func

router = APIRouter()

_CORE_BOUND = False


def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    names = [
        'render_backend_page',
        '_load_plantillas_store',
        '_save_plantillas_store',
        'SYSTEM_REPORT_HEADER_TEMPLATE_ID',
        '_normalize_tenant_id',
        'get_current_tenant',
        'is_superadmin',
        'is_admin',
        'get_current_role',
        'normalize_role_name',
        'require_admin_or_superadmin',
        'slugify_value',
        'FormDefinition',
        'FormDefinitionCreateSchema',
        'FormDefinitionResponseSchema',
        'FormField',
        'FormSubmission',
        'FormRenderer',
        'Rol',
        'get_db',
        '_build_submission_export_columns',
        '_normalize_submission_value',
        '_normalize_form_submission_payload',
        'send_form_submission_email_notification',
        'send_form_submission_webhooks',
        '_get_login_identity_context',
    ]
    for name in names:
        globals()[name] = getattr(core, name)
    _CORE_BOUND = True


def get_db():
    _bind_core_symbols()
    yield from globals()['get_db']()


def get_db_proxy():
    _bind_core_symbols()
    yield from globals()['get_db']()


@router.get("/plantillas", response_class=HTMLResponse)
def plantillas_page(request: Request):
    _bind_core_symbols()
    plantillas_content = """
        <section id="plantillas-page" class="w-full">
            <div class="titulo bg-base-200 rounded-box border border-base-300 p-4 sm:p-6 mb-4">
                <div class="w-full flex flex-col md:flex-row items-center gap-10">
                    <img
                        src="/icon/empresa.svg"
                        alt="Icono empresa"
                        width="96"
                        height="96"
                        class="shrink-0 rounded-box border border-base-300 bg-base-100 p-3 object-contain"
                    />
                    <div class="w-full grid gap-2 content-center">
                        <div class="block w-full text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight text-[color:var(--sidebar-bottom)]">Plantillas</div>
                        <div class="block w-full text-base sm:text-lg text-base-content/70">Crea y administra plantillas base de la organización.</div>
                    </div>
                </div>
            </div>
            <div class="grid grid-cols-1 xl:grid-cols-12 gap-4">
                <aside class="card border border-base-300 bg-base-100 shadow-sm xl:col-span-3">
                    <div class="card-body gap-3">
                        <h3 class="card-title text-base">Plantillas</h3>
                        <p class="text-sm text-base-content/70">Selecciona una plantilla existente o crea una nueva desde la barra flotante. "Encabezado" es la base para todos los reportes.</p>
                        <ul id="plantillas-list" class="menu bg-base-100 rounded-box"></ul>
                    </div>
                </aside>
                <section class="card border border-base-300 bg-base-100 shadow-sm xl:col-span-9">
                    <div class="card-body gap-4">
                        <div class="form-control gap-1">
                            <label for="template-name" class="label"><span class="label-text">Nombre de plantilla</span></label>
                            <input type="text" id="template-name" class="input input-bordered w-full" placeholder="Ej: Tarjeta institucional">
                        </div>
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-3">
                            <div class="form-control gap-1">
                                <label for="template-html" class="label"><span class="label-text">HTML</span></label>
                                <textarea id="template-html" class="textarea textarea-bordered w-full min-h-[240px] font-mono text-xs" placeholder="<section class='card'>...</section>"></textarea>
                            </div>
                            <div class="form-control gap-1">
                                <label for="template-css" class="label"><span class="label-text">CSS</span></label>
                                <textarea id="template-css" class="textarea textarea-bordered w-full min-h-[240px] font-mono text-xs" placeholder=".card { padding: 16px; border-radius: 12px; }"></textarea>
                            </div>
                        </div>
                        <div class="flex flex-wrap items-center justify-between gap-2">
                            <h4 class="text-sm font-semibold">Vista previa</h4>
                            <div class="flex flex-wrap items-center gap-2">
                                <button type="button" id="template-builder-btn" class="btn btn-sm btn-outline">Construir formulario</button>
                                <button type="button" id="template-preview-btn" class="btn btn-sm btn-outline">Previsualizar</button>
                            </div>
                        </div>
                        <div class="botones_accion">
                            <button type="button" id="template-new-btn" class="view-pill boton_vista" data-tooltip="Nuevo" aria-label="Nuevo" title="Nuevo">
                                <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/nuevo.svg')"></span>
                                <span class="boton_vista-label">Nuevo</span>
                            </button>
                            <button type="button" id="template-edit-btn" class="view-pill boton_vista" data-tooltip="Editar" aria-label="Editar" title="Editar">
                                <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/editar.svg')"></span>
                                <span class="boton_vista-label">Editar</span>
                            </button>
                            <button type="button" id="template-save-btn" class="view-pill boton_vista" data-tooltip="Guardar" aria-label="Guardar" title="Guardar">
                                <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/guardar.svg')"></span>
                                <span class="boton_vista-label">Guardar</span>
                            </button>
                            <button type="button" id="template-delete-btn" class="view-pill boton_vista" data-tooltip="Eliminar" aria-label="Eliminar" title="Eliminar">
                                <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/eliminar.svg')"></span>
                                <span class="boton_vista-label">Eliminar</span>
                            </button>
                        </div>
                        <iframe id="template-preview" class="w-full min-h-[280px] rounded-box border border-base-300 bg-base-100" title="Vista previa de plantilla"></iframe>
                        <section id="form-builder-panel" class="hidden card border border-base-300 bg-base-100" aria-label="Constructor de formularios">
                            <div class="card-body gap-4">
                                <div>
                                    <h4 class="text-base font-semibold">Constructor de formularios</h4>
                                    <p class="text-sm text-base-content/70">Crea formularios dinámicos para usuarios finales.</p>
                                </div>
                                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                                    <div class="form-control gap-1">
                                        <label for="builder-form-select" class="label"><span class="label-text">Formularios existentes</span></label>
                                        <select id="builder-form-select" class="select select-bordered w-full">
                                            <option value="">Nuevo formulario</option>
                                        </select>
                                    </div>
                                    <div class="form-control gap-1">
                                        <label for="builder-form-name" class="label"><span class="label-text">Nombre</span></label>
                                        <input type="text" id="builder-form-name" class="input input-bordered w-full" placeholder="Ej: Solicitud de crédito">
                                    </div>
                                    <div class="form-control gap-1">
                                        <label for="builder-form-slug" class="label"><span class="label-text">Slug (opcional)</span></label>
                                        <input type="text" id="builder-form-slug" class="input input-bordered w-full" placeholder="solicitud-credito">
                                    </div>
                                    <div class="form-control gap-1">
                                        <label for="builder-form-active" class="label"><span class="label-text">Estado</span></label>
                                        <select id="builder-form-active" class="select select-bordered w-full">
                                            <option value="true">Activo</option>
                                            <option value="false">Inactivo</option>
                                        </select>
                                    </div>
                                    <div class="form-control gap-1">
                                        <label for="builder-form-tenant" class="label"><span class="label-text">Tenant</span></label>
                                        <input type="text" id="builder-form-tenant" class="input input-bordered w-full" placeholder="default">
                                    </div>
                                    <div class="form-control gap-1">
                                        <label for="builder-form-roles" class="label"><span class="label-text">Roles permitidos</span></label>
                                        <select id="builder-form-roles" class="select select-bordered w-full" multiple></select>
                                    </div>
                                    <div class="form-control gap-1 md:col-span-2 xl:col-span-3">
                                        <label for="builder-form-description" class="label"><span class="label-text">Descripción</span></label>
                                        <textarea id="builder-form-description" class="textarea textarea-bordered w-full" placeholder="Descripción del formulario"></textarea>
                                    </div>
                                    <div class="form-control gap-1 md:col-span-2 xl:col-span-3">
                                        <label for="builder-form-config" class="label"><span class="label-text">Configuración (JSON)</span></label>
                                        <textarea id="builder-form-config" class="textarea textarea-bordered w-full" placeholder='{"wizard":{"steps":[{"title":"Paso 1","fields":["nombre","email"]},{"title":"Paso 2","fields":["tipo","detalle"]}]},"notifications":{"email":{"enabled":true,"to":["equipo@empresa.com"],"cc":[],"subject":"Nuevo envio"},"webhooks":[{"url":"https://api.empresa.com/hook/forms","method":"POST"}]}}'></textarea>
                                    </div>
                                </div>
                                <div class="card border border-base-300 bg-base-100">
                                    <div class="card-body gap-3">
                                        <h5 class="font-semibold">Agregar campo</h5>
                                        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                                            <div class="form-control gap-1">
                                                <label for="builder-field-type" class="label"><span class="label-text">Tipo</span></label>
                                                <select id="builder-field-type" class="select select-bordered w-full">
                                                    <option value="text">Texto corto</option>
                                                    <option value="textarea">Texto largo</option>
                                                    <option value="email">Email</option>
                                                    <option value="password">Contraseña</option>
                                                    <option value="number">Número (decimal)</option>
                                                    <option value="integer">Número (entero)</option>
                                                    <option value="select">Desplegable (Dropdown)</option>
                                                    <option value="checkboxes">Opción múltiple (Checkboxes)</option>
                                                    <option value="radio">Opción única (Radio)</option>
                                                    <option value="likert">Escala Likert</option>
                                                    <option value="checkbox">Checkbox</option>
                                                    <option value="date">Selector de fecha</option>
                                                    <option value="time">Selector de hora</option>
                                                    <option value="daterange">Rango de fechas</option>
                                                    <option value="file">Carga de archivos</option>
                                                    <option value="signature">Firma digital</option>
                                                    <option value="url">Enlace (URL)</option>
                                                    <option value="header">Encabezado</option>
                                                    <option value="paragraph">Texto estático (Paragraph)</option>
                                                    <option value="html">Texto estático (HTML)</option>
                                                    <option value="divider">Separador</option>
                                                    <option value="pagebreak">Salto de página</option>
                                                </select>
                                            </div>
                                            <div class="form-control gap-1">
                                                <label for="builder-field-label" class="label"><span class="label-text">Etiqueta</span></label>
                                                <input type="text" id="builder-field-label" class="input input-bordered w-full" placeholder="Nombre completo">
                                            </div>
                                            <div class="form-control gap-1">
                                                <label for="builder-field-name" class="label"><span class="label-text">Nombre técnico</span></label>
                                                <input type="text" id="builder-field-name" class="input input-bordered w-full" placeholder="nombre_completo">
                                            </div>
                                            <div class="form-control gap-1">
                                                <label for="builder-field-placeholder" class="label"><span class="label-text">Placeholder</span></label>
                                                <input type="text" id="builder-field-placeholder" class="input input-bordered w-full" placeholder="Escribe aquí">
                                            </div>
                                            <div class="form-control gap-1">
                                                <label for="builder-field-help" class="label"><span class="label-text">Ayuda</span></label>
                                                <input type="text" id="builder-field-help" class="input input-bordered w-full" placeholder="Texto de ayuda">
                                            </div>
                                            <div class="form-control gap-1">
                                                <label for="builder-field-options" class="label"><span class="label-text">Opciones (select/radio)</span></label>
                                                <input type="text" id="builder-field-options" class="input input-bordered w-full" placeholder="Opción A, Opción B, Opción C">
                                            </div>
                                            <div class="form-control gap-1">
                                                <label for="builder-field-conditional" class="label"><span class="label-text">Condicional (JSON)</span></label>
                                                <input type="text" id="builder-field-conditional" class="input input-bordered w-full" placeholder='{"field":"tipo","operator":"equals","value":"staff"}'>
                                            </div>
                                            <div class="form-control gap-2">
                                                <label for="builder-field-required" class="label cursor-pointer justify-start gap-2">
                                                    <input type="checkbox" id="builder-field-required" class="checkbox checkbox-sm">
                                                    <span class="label-text">Obligatorio</span>
                                                </label>
                                            </div>
                                        </div>
                                        <div class="flex flex-wrap gap-2">
                                            <button type="button" id="builder-add-field-btn" class="btn btn-sm btn-outline">Agregar campo</button>
                                            <button type="button" id="builder-clear-form-btn" class="btn btn-sm btn-outline">Limpiar</button>
                                            <button type="button" id="builder-save-form-btn" class="btn btn-sm btn-primary">Guardar formulario</button>
                                            <button type="button" id="builder-delete-form-btn" class="btn btn-sm btn-error btn-outline">Eliminar formulario</button>
                                        </div>
                                    </div>
                                </div>
                                <div class="space-y-2">
                                    <h5 class="font-semibold">Campos del formulario</h5>
                                    <div id="builder-fields-list" class="space-y-2"></div>
                                </div>
                            </div>
                        </section>
                    </div>
                </section>
            </div>
        </section>
    """
    return render_backend_page(
        request,
        title="Plantillas",
        description="Crea y guarda plantillas con HTML y CSS.",
        content=plantillas_content,
        hide_floating_actions=False,
        floating_actions_screen="plantillas",
        show_page_header=False,
    )


@router.get("/plantillas/constructor", response_class=HTMLResponse)
def plantillas_constructor_page(request: Request):
    _bind_core_symbols()
    constructor_content = """
        <section id="plantillas-page" class="w-full">
            <div class="titulo bg-base-200 rounded-box border border-base-300 p-4 sm:p-6 mb-4">
                <div class="w-full flex flex-col md:flex-row items-center gap-10">
                    <img
                        src="/icon/empresa.svg"
                        alt="Icono empresa"
                        width="96"
                        height="96"
                        class="shrink-0 rounded-box border border-base-300 bg-base-100 p-3 object-contain"
                    />
                    <div class="w-full grid gap-2 content-center">
                        <div class="block w-full text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight text-[color:var(--sidebar-bottom)]">Constructor de formularios</div>
                        <div class="block w-full text-base sm:text-lg text-base-content/70">Diseña formularios dinámicos para procesos de la empresa.</div>
                    </div>
                </div>
            </div>
            <div class="grid grid-cols-1 xl:grid-cols-12 gap-4">
                <aside class="card border border-base-300 bg-base-100 shadow-sm xl:col-span-3">
                    <div class="card-body gap-3">
                        <h3 class="card-title text-base">Constructor de formularios</h3>
                        <p class="text-sm text-base-content/70">Pantalla dedicada para crear, editar y publicar formularios dinámicos.</p>
                        <div class="flex flex-wrap gap-2">
                            <button type="button" id="builder-back-to-templates" class="btn btn-sm btn-outline">Volver a plantillas</button>
                        </div>
                    </div>
                </aside>
                <section class="card border border-base-300 bg-base-100 shadow-sm xl:col-span-9">
                    <div class="card-body gap-4">
                        <section id="form-builder-panel" class="space-y-4" aria-label="Constructor de formularios">
                            <div>
                                <h4 class="text-base font-semibold">Constructor de formularios</h4>
                                <p class="text-sm text-base-content/70">Crea formularios dinámicos para usuarios finales.</p>
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                                <div class="form-control gap-1">
                                    <label for="builder-form-select" class="label"><span class="label-text">Formulario</span></label>
                                    <select id="builder-form-select" class="select select-bordered w-full">
                                        <option value="">Nuevo formulario</option>
                                    </select>
                                </div>
                                <div class="form-control gap-1">
                                    <label for="builder-form-name" class="label"><span class="label-text">Nombre</span></label>
                                    <input type="text" id="builder-form-name" class="input input-bordered w-full" placeholder="Ej: Solicitud de apoyo">
                                </div>
                                <div class="form-control gap-1">
                                    <label for="builder-form-slug" class="label"><span class="label-text">Slug</span></label>
                                    <input type="text" id="builder-form-slug" class="input input-bordered w-full" placeholder="solicitud-apoyo">
                                </div>
                                <div class="form-control gap-1">
                                    <label for="builder-form-active" class="label"><span class="label-text">Estado</span></label>
                                    <select id="builder-form-active" class="select select-bordered w-full">
                                        <option value="true">Activo</option>
                                        <option value="false">Inactivo</option>
                                    </select>
                                </div>
                                <div class="form-control gap-1">
                                    <label for="builder-form-tenant" class="label"><span class="label-text">Tenant</span></label>
                                    <input type="text" id="builder-form-tenant" class="input input-bordered w-full" placeholder="default">
                                </div>
                                <div class="form-control gap-1">
                                    <label for="builder-form-roles" class="label"><span class="label-text">Roles permitidos</span></label>
                                    <select id="builder-form-roles" class="select select-bordered w-full" multiple></select>
                                </div>
                                <div class="form-control gap-1 md:col-span-2 xl:col-span-3">
                                    <label for="builder-form-description" class="label"><span class="label-text">Descripción</span></label>
                                    <textarea id="builder-form-description" class="textarea textarea-bordered w-full" placeholder="Describe el objetivo del formulario"></textarea>
                                </div>
                                <div class="form-control gap-1 md:col-span-2 xl:col-span-3">
                                    <label for="builder-form-config" class="label"><span class="label-text">Configuración JSON (opcional)</span></label>
                                    <textarea id="builder-form-config" class="textarea textarea-bordered w-full" placeholder='{"submitLabel":"Enviar"}'></textarea>
                                </div>
                            </div>
                            <div class="card border border-base-300 bg-base-100">
                                <div class="card-body gap-3">
                                    <h5 class="font-semibold">Campos del formulario</h5>
                                    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                                        <div class="form-control gap-1">
                                            <label for="builder-field-type" class="label"><span class="label-text">Tipo</span></label>
                                            <select id="builder-field-type" class="select select-bordered w-full">
                                                <option value="text">Texto</option>
                                                <option value="email">Email</option>
                                                <option value="number">Número</option>
                                                <option value="date">Fecha</option>
                                                <option value="select">Selección</option>
                                                <option value="radio">Opciones (radio)</option>
                                                <option value="checkboxes">Opciones (checkbox)</option>
                                                <option value="textarea">Texto largo</option>
                                                <option value="file">Archivo</option>
                                                <option value="password">Contraseña</option>
                                                <option value="likert">Likert</option>
                                            </select>
                                        </div>
                                        <div class="form-control gap-1">
                                            <label for="builder-field-label" class="label"><span class="label-text">Etiqueta</span></label>
                                            <input type="text" id="builder-field-label" class="input input-bordered w-full" placeholder="Nombre completo">
                                        </div>
                                        <div class="form-control gap-1">
                                            <label for="builder-field-name" class="label"><span class="label-text">Nombre técnico</span></label>
                                            <input type="text" id="builder-field-name" class="input input-bordered w-full" placeholder="nombre_completo">
                                        </div>
                                        <div class="form-control gap-1">
                                            <label for="builder-field-placeholder" class="label"><span class="label-text">Placeholder</span></label>
                                            <input type="text" id="builder-field-placeholder" class="input input-bordered w-full" placeholder="Escribe aquí...">
                                        </div>
                                        <div class="form-control gap-1">
                                            <label for="builder-field-help" class="label"><span class="label-text">Ayuda</span></label>
                                            <input type="text" id="builder-field-help" class="input input-bordered w-full" placeholder="Texto de apoyo">
                                        </div>
                                        <div class="form-control gap-1">
                                            <label for="builder-field-options" class="label"><span class="label-text">Opciones (coma separadas)</span></label>
                                            <input type="text" id="builder-field-options" class="input input-bordered w-full" placeholder="A, B, C">
                                        </div>
                                        <div class="form-control gap-1">
                                            <label for="builder-field-conditional" class="label"><span class="label-text">Condición JSON</span></label>
                                            <input type="text" id="builder-field-conditional" class="input input-bordered w-full" placeholder='{"depends_on":"campo","equals":"valor"}'>
                                        </div>
                                        <div class="form-control gap-2">
                                            <label for="builder-field-required" class="label cursor-pointer justify-start gap-2">
                                                <input type="checkbox" id="builder-field-required" class="checkbox checkbox-sm">
                                                <span class="label-text">Obligatorio</span>
                                            </label>
                                        </div>
                                    </div>
                                    <div class="flex flex-wrap gap-2">
                                        <button type="button" id="builder-add-field-btn" class="btn btn-sm btn-outline">Agregar campo</button>
                                        <button type="button" id="builder-clear-form-btn" class="btn btn-sm btn-outline">Limpiar</button>
                                        <button type="button" id="builder-save-form-btn" class="btn btn-sm btn-primary">Guardar formulario</button>
                                        <button type="button" id="builder-delete-form-btn" class="btn btn-sm btn-error btn-outline">Eliminar formulario</button>
                                    </div>
                                </div>
                            </div>
                            <div class="space-y-2">
                                <h5 class="font-semibold">Campos agregados</h5>
                                <div id="builder-fields-list" class="space-y-2"></div>
                            </div>
                        </section>
                    </div>
                </section>
            </div>
        </section>
    """
    return render_backend_page(
        request,
        title="Constructor de formularios",
        description="Crea formularios dinámicos en una pantalla dedicada.",
        content=constructor_content,
        hide_floating_actions=False,
        floating_actions_screen="plantillas",
        show_page_header=False,
    )


@router.get("/api/plantillas")
def listar_plantillas():
    _bind_core_symbols()
    return JSONResponse({"success": True, "data": _load_plantillas_store()})


@router.post("/api/plantillas")
def guardar_plantilla(data: dict = Body(...)):
    _bind_core_symbols()
    nombre = (data.get("nombre") or "").strip()
    html_code = data.get("html") or ""
    css_code = data.get("css") or ""
    template_id = (data.get("id") or "").strip()
    if not nombre:
        return JSONResponse({"success": False, "error": "El nombre es obligatorio"}, status_code=400)
    if not html_code.strip() and not css_code.strip():
        return JSONResponse({"success": False, "error": "Debes agregar HTML o CSS"}, status_code=400)

    templates = _load_plantillas_store()
    now_iso = datetime.utcnow().isoformat()
    if template_id:
        updated = False
        for template in templates:
            if template.get("id") == template_id:
                template["nombre"] = nombre
                template["html"] = html_code
                template["css"] = css_code
                template["updated_at"] = now_iso
                updated = True
                break
        if not updated:
            return JSONResponse({"success": False, "error": "Plantilla no encontrada"}, status_code=404)
    else:
        template_id = secrets.token_hex(8)
        templates.insert(
            0,
            {
                "id": template_id,
                "nombre": nombre,
                "html": html_code,
                "css": css_code,
                "created_at": now_iso,
                "updated_at": now_iso,
            },
        )
    _save_plantillas_store(templates)
    return JSONResponse({"success": True, "data": {"id": template_id}})


def _forms_scope_query_by_tenant(query, request: Request):
    _bind_core_symbols()
    tenant_id = _normalize_tenant_id(get_current_tenant(request))
    if is_superadmin(request):
        header_tenant = request.headers.get("x-tenant-id")
        if header_tenant and _normalize_tenant_id(header_tenant) != "all":
            return query.filter(func.lower(FormDefinition.tenant_id) == _normalize_tenant_id(header_tenant).lower())
        if not header_tenant:
            return query.filter(func.lower(FormDefinition.tenant_id) == tenant_id.lower())
        return query
    return query.filter(func.lower(FormDefinition.tenant_id) == tenant_id.lower())


def _resolve_form_tenant_for_write(request: Request, requested_tenant: Optional[str]) -> str:
    _bind_core_symbols()
    if is_superadmin(request):
        if requested_tenant:
            return _normalize_tenant_id(requested_tenant)
        header_tenant = request.headers.get("x-tenant-id")
        if header_tenant and _normalize_tenant_id(header_tenant) != "all":
            return _normalize_tenant_id(header_tenant)
    return _normalize_tenant_id(get_current_tenant(request))


def _normalize_form_allowed_roles(request: Request, db, raw_roles: Any) -> List[str]:
    _bind_core_symbols()
    allowed = {
        normalize_role_name(role.nombre)
        for role in db.query(Rol).all()
        if (role.nombre or "").strip()
    }
    if is_admin(request):
        allowed = {item for item in allowed if item != "superadministrador"}
    normalized_roles: List[str] = []
    if isinstance(raw_roles, list):
        for role in raw_roles:
            role_name = normalize_role_name(str(role))
            if role_name in allowed:
                normalized_roles.append(role_name)
    return sorted(set(normalized_roles))


def _form_role_is_allowed(form: FormDefinition, request: Request) -> bool:
    _bind_core_symbols()
    if is_superadmin(request):
        return True
    allowed_roles_raw = form.allowed_roles if isinstance(form.allowed_roles, list) else []
    if not allowed_roles_raw:
        return True
    allowed_roles = {normalize_role_name(str(item)) for item in allowed_roles_raw if str(item).strip()}
    return get_current_role(request) in allowed_roles


def _get_form_by_id_for_request(db, form_id: int, request: Request) -> FormDefinition:
    _bind_core_symbols()
    query = _forms_scope_query_by_tenant(
        db.query(FormDefinition).filter(FormDefinition.id == form_id),
        request,
    )
    form = query.first()
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    return form


def _get_form_by_slug_for_request(db, slug: str, request: Request, active_only: bool = True) -> FormDefinition:
    _bind_core_symbols()
    query = db.query(FormDefinition).filter(FormDefinition.slug == slug)
    if active_only:
        query = query.filter(FormDefinition.is_active == True)  # noqa: E712
    query = _forms_scope_query_by_tenant(query, request)
    form = query.first()
    if not form:
        raise HTTPException(status_code=404, detail="Formulario no encontrado")
    if not _form_role_is_allowed(form, request):
        raise HTTPException(status_code=403, detail="Tu rol no tiene acceso a este formulario")
    return form


@router.post("/api/admin/forms")
def create_form_definition(
    request: Request,
    payload: Dict[str, Any] = Body(default_factory=dict),
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    form_data = FormDefinitionCreateSchema.model_validate(payload)
    require_admin_or_superadmin(request)
    slug = slugify_value(form_data.slug or form_data.name)
    existing = db.query(FormDefinition).filter(FormDefinition.slug == slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="El slug ya existe")

    tenant_id = _resolve_form_tenant_for_write(request, form_data.tenant_id)
    allowed_roles = _normalize_form_allowed_roles(request, db, form_data.allowed_roles)
    form = FormDefinition(
        name=form_data.name,
        slug=slug,
        tenant_id=tenant_id,
        description=form_data.description,
        config=form_data.config or {},
        allowed_roles=allowed_roles,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=form_data.is_active,
    )
    db.add(form)
    db.flush()

    for field_data in form_data.fields:
        db.add(
            FormField(
                form_id=form.id,
                field_type=field_data.field_type,
                label=field_data.label,
                name=field_data.name,
                placeholder=field_data.placeholder,
                help_text=field_data.help_text,
                default_value=field_data.default_value,
                is_required=field_data.is_required,
                validation_rules=field_data.validation_rules,
                options=field_data.options,
                order=field_data.order,
                conditional_logic=field_data.conditional_logic,
            )
        )

    db.commit()
    db.refresh(form)
    return form


@router.get("/api/admin/forms")
def list_form_definitions(
    request: Request,
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    require_admin_or_superadmin(request)
    query = _forms_scope_query_by_tenant(db.query(FormDefinition), request)
    return query.order_by(FormDefinition.id.desc()).all()


@router.get("/api/admin/forms/{form_id}")
def get_form_definition(
    form_id: int,
    request: Request,
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    require_admin_or_superadmin(request)
    return _get_form_by_id_for_request(db, form_id, request)


@router.put("/api/admin/forms/{form_id}")
def update_form_definition(
    form_id: int,
    request: Request,
    payload: Dict[str, Any] = Body(default_factory=dict),
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    form_data = FormDefinitionCreateSchema.model_validate(payload)
    require_admin_or_superadmin(request)
    form = _get_form_by_id_for_request(db, form_id, request)

    new_slug = slugify_value(form_data.slug or form_data.name)
    duplicate = (
        db.query(FormDefinition)
        .filter(FormDefinition.slug == new_slug, FormDefinition.id != form_id)
        .first()
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="El slug ya existe")

    form.name = form_data.name
    form.slug = new_slug
    form.tenant_id = _resolve_form_tenant_for_write(request, form_data.tenant_id or form.tenant_id)
    form.description = form_data.description
    form.config = form_data.config or {}
    form.allowed_roles = _normalize_form_allowed_roles(request, db, form_data.allowed_roles)
    form.is_active = form_data.is_active
    form.updated_at = datetime.utcnow()
    db.add(form)

    db.query(FormField).filter(FormField.form_id == form_id).delete()
    for field_data in form_data.fields:
        db.add(
            FormField(
                form_id=form_id,
                field_type=field_data.field_type,
                label=field_data.label,
                name=field_data.name,
                placeholder=field_data.placeholder,
                help_text=field_data.help_text,
                default_value=field_data.default_value,
                is_required=field_data.is_required,
                validation_rules=field_data.validation_rules,
                options=field_data.options,
                order=field_data.order,
                conditional_logic=field_data.conditional_logic,
            )
        )

    db.commit()
    return {"success": True, "message": "Formulario actualizado"}


@router.delete("/api/admin/forms/{form_id}")
def delete_form_definition(
    form_id: int,
    request: Request,
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    require_admin_or_superadmin(request)
    form = _get_form_by_id_for_request(db, form_id, request)
    db.delete(form)
    db.commit()
    return {"success": True, "message": "Formulario eliminado"}


@router.get("/api/admin/forms/{form_id}/submissions/export/{formato}")
def export_form_submissions(
    form_id: int,
    formato: str,
    request: Request,
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    require_admin_or_superadmin(request)
    form = _get_form_by_id_for_request(db, form_id, request)

    submissions = (
        db.query(FormSubmission)
        .filter(FormSubmission.form_id == form_id)
        .order_by(FormSubmission.submitted_at.asc(), FormSubmission.id.asc())
        .all()
    )
    columns = _build_submission_export_columns(form, submissions)
    base_headers = ["submission_id", "submitted_at", "ip_address", "user_agent"]
    headers = [*base_headers, *columns]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_slug = slugify_value(form.slug or form.name)

    if formato.lower() == "csv":
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=headers)
        writer.writeheader()
        for submission in submissions:
            data = submission.data if isinstance(submission.data, dict) else {}
            row = {
                "submission_id": submission.id,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else "",
                "ip_address": submission.ip_address or "",
                "user_agent": submission.user_agent or "",
            }
            for field_name in columns:
                row[field_name] = _normalize_submission_value(data.get(field_name))
            writer.writerow(row)
        filename = f"{safe_slug}_submissions_{timestamp}.csv"
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if formato.lower() in {"excel", "xlsx"}:
        records = []
        for submission in submissions:
            data = submission.data if isinstance(submission.data, dict) else {}
            record = {
                "submission_id": submission.id,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else "",
                "ip_address": submission.ip_address or "",
                "user_agent": submission.user_agent or "",
            }
            for field_name in columns:
                record[field_name] = _normalize_submission_value(data.get(field_name))
            records.append(record)
        df = pd.DataFrame(records, columns=headers)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Submissions")
        filename = f"{safe_slug}_submissions_{timestamp}.xlsx"
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    raise HTTPException(status_code=400, detail="Formato no soportado. Usa csv o excel")


@router.get("/api/forms/{slug}")
def get_public_form_definition(
    slug: str,
    request: Request,
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    form = _get_form_by_slug_for_request(db, slug, request, active_only=True)
    return {"success": True, "data": FormRenderer.render_to_json(form)}


@router.post("/api/forms/{slug}/submit")
def submit_public_form(
    slug: str,
    request: Request,
    payload: Dict[str, Any] = Body(default_factory=dict),
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    form = _get_form_by_slug_for_request(db, slug, request, active_only=True)

    normalized_payload = _normalize_form_submission_payload(form, payload)
    visible_fields = FormRenderer.visible_field_names(form, normalized_payload)
    dynamic_model = FormRenderer.generate_pydantic_model(form, visible_field_names=visible_fields)
    try:
        validated = dynamic_model.model_validate(normalized_payload)
        validated_data = validated.model_dump()
        FormRenderer._apply_custom_rules(form, validated_data, visible_field_names=visible_fields)
    except ValidationError as exc:
        return JSONResponse(
            {"success": False, "error": "Datos inválidos", "details": exc.errors()},
            status_code=422,
        )
    except ValueError as exc:
        return JSONResponse(
            {"success": False, "error": str(exc)},
            status_code=422,
        )
    validated_data = {key: value for key, value in validated_data.items() if key in visible_fields}

    submission = FormSubmission(
        form_id=form.id,
        data=validated_data,
        submitted_at=datetime.utcnow(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    email_status = send_form_submission_email_notification(form, submission)
    webhook_status = send_form_submission_webhooks(form, submission)

    return {
        "success": True,
        "message": "Formulario enviado correctamente",
        "submission_id": submission.id,
        "notification": {
            "email": email_status,
            "webhooks": webhook_status,
        },
    }


@router.get("/forms/{slug}", response_class=HTMLResponse)
def render_public_form(
    slug: str,
    request: Request,
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    form = _get_form_by_slug_for_request(db, slug, request, active_only=True)
    login_identity = _get_login_identity_context()
    return request.app.state.templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "title": form.name,
            "form": form,
            "form_json": json.dumps(FormRenderer.render_to_json(form), ensure_ascii=False),
            "app_favicon_url": login_identity.get("login_favicon_url"),
        },
    )


@router.get("/forms/api/{slug}")
def get_public_form_definition_v2(
    slug: str,
    request: Request,
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    form = _get_form_by_slug_for_request(db, slug, request, active_only=True)
    return {"success": True, "data": FormRenderer.render_to_json(form)}


@router.post("/forms/api/{slug}/submit")
async def submit_public_form_v2(
    slug: str,
    request: Request,
    db=Depends(get_db_proxy),
):
    _bind_core_symbols()
    form = _get_form_by_slug_for_request(db, slug, request, active_only=True)

    form_data = await request.form()
    payload: Dict[str, Any] = {}
    for key in form_data.keys():
        values = form_data.getlist(key)
        payload[key] = values if len(values) > 1 else values[0]
    normalized_payload = _normalize_form_submission_payload(form, payload)
    visible_fields = FormRenderer.visible_field_names(form, normalized_payload)
    dynamic_model = FormRenderer.generate_pydantic_model(form, visible_field_names=visible_fields)
    try:
        validated = dynamic_model.model_validate(normalized_payload)
        validated_data = validated.model_dump()
        FormRenderer._apply_custom_rules(form, validated_data, visible_field_names=visible_fields)
    except ValidationError as exc:
        return JSONResponse(
            {"success": False, "error": "Datos inválidos", "details": exc.errors()},
            status_code=422,
        )
    except ValueError as exc:
        return JSONResponse(
            {"success": False, "error": str(exc)},
            status_code=422,
        )
    validated_data = {key: value for key, value in validated_data.items() if key in visible_fields}

    submission = FormSubmission(
        form_id=form.id,
        data=validated_data,
        submitted_at=datetime.utcnow(),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    email_status = send_form_submission_email_notification(form, submission)
    webhook_status = send_form_submission_webhooks(form, submission)
    return {
        "success": True,
        "message": "Formulario enviado correctamente",
        "submission_id": submission.id,
        "notification": {
            "email": email_status,
            "webhooks": webhook_status,
        },
    }


@router.delete("/api/plantillas/{template_id}")
def eliminar_plantilla(template_id: str):
    _bind_core_symbols()
    template_id = (template_id or "").strip()
    if not template_id:
        return JSONResponse({"success": False, "error": "ID de plantilla invalido"}, status_code=400)
    if template_id == SYSTEM_REPORT_HEADER_TEMPLATE_ID:
        return JSONResponse(
            {"success": False, "error": "La plantilla Encabezado es obligatoria para reportes"},
            status_code=400,
        )

    templates = _load_plantillas_store()
    remaining = [tpl for tpl in templates if str(tpl.get("id", "")).strip() != template_id]
    if len(remaining) == len(templates):
        return JSONResponse({"success": False, "error": "Plantilla no encontrada"}, status_code=404)
    _save_plantillas_store(remaining)
    return JSONResponse({"success": True})
