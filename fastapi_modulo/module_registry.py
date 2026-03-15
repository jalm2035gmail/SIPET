from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from typing import Any, Dict, Iterable, List, Optional

from fastapi import FastAPI
from sqlalchemy import text

from fastapi_modulo.db import engine


@dataclass
class RouterSpec:
    module_path: str
    attr_name: str = "router"
    include_kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModuleDefinition:
    key: str
    label: str
    description: str
    route: str = ""
    icon: str = ""
    metadata_file: str = ""
    manifest_file: str = ""
    app_access_name: Optional[str] = None
    sidebar_visible: bool = True
    manageable: bool = True
    always_enabled: bool = False
    default_enabled: bool = True
    boot_strategy: str = "deferred_router"
    registration_phase: str = "startup"
    router_specs: List[RouterSpec] = field(default_factory=list)


MODULE_DEFINITIONS: List[ModuleDefinition] = [
    ModuleDefinition(
        key="backend",
        label="backend",
        description="Sitio backend y constructor frontend.",
        route="/backend",
        icon="fa-solid fa-globe",
        sidebar_visible=True,
        manageable=True,
        registration_phase="late",
        router_specs=[
            RouterSpec("fastapi_modulo.modulos.backend.controladores.backend_auth"),
            RouterSpec("fastapi_modulo.modulos.frontend.controladores.frontend"),
        ],
    ),
    ModuleDefinition(
        key="mi_tablero",
        label="Mi tablero",
        description="Vista personal y accesos rápidos del usuario.",
        route="/mi-tablero",
        icon="fa-regular fa-rectangle-list",
        app_access_name="Mi tablero",
        sidebar_visible=True,
        manageable=True,
        boot_strategy="builtin",
        router_specs=[
            RouterSpec("fastapi_modulo.modulos.main.controladores.inicio"),
            RouterSpec("fastapi_modulo.modulos.main.controladores.usuarios"),
            RouterSpec("fastapi_modulo.modulos.main.controladores.ajustes"),
        ],
    ),
    ModuleDefinition(
        key="conversaciones",
        label="Conversaciones",
        description="Notificaciones internas y mensajería.",
        route="/notificaciones",
        icon="fa-regular fa-envelope",
        metadata_file="fastapi_modulo/modulos/notificaciones/modulo.json",
        app_access_name="Conversaciones",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.notificaciones.controladores.notificaciones")],
    ),
    ModuleDefinition(
        key="organizacion",
        label="Organización",
        description="Usuarios, empleados, regiones y departamentos.",
        route="/inicio/departamentos",
        icon="fa-solid fa-sitemap",
        app_access_name="Organización",
        sidebar_visible=True,
        manageable=True,
        router_specs=[
            RouterSpec("fastapi_modulo.modulos.empleados.controladores.empleados"),
            RouterSpec("fastapi_modulo.modulos.empleados.controladores.regiones"),
            RouterSpec("fastapi_modulo.modulos.empleados.controladores.departamentos"),
        ],
    ),
    ModuleDefinition(
        key="estrategia_tactica",
        label="Estrategia y táctica",
        description="Planificación, POA, ciclo anual y tablero estratégico.",
        route="/planes",
        icon="fa-solid fa-chess-board",
        app_access_name="Estrategia y táctica",
        sidebar_visible=True,
        manageable=True,
        router_specs=[
            RouterSpec("fastapi_modulo.modulos.planificacion.controladores.annual_cycle_service"),
            RouterSpec("fastapi_modulo.modulos.planificacion.controladores.plan_estrategico"),
            RouterSpec("fastapi_modulo.modulos.planificacion.controladores.poa"),
            RouterSpec("fastapi_modulo.modulos.planificacion.controladores.kpis"),
            RouterSpec("fastapi_modulo.modulos.planificacion.controladores.notificaciones"),
            RouterSpec("fastapi_modulo.modulos.planificacion.controladores.ejes_poa"),
        ],
    ),
    ModuleDefinition(
        key="datos_financieros",
        label="Datos financieros",
        description="Proyecciones y herramientas financieras.",
        route="/proyectando",
        icon="fa-solid fa-chart-column",
        app_access_name="Datos financieros",
        sidebar_visible=True,
        manageable=True,
        router_specs=[
            RouterSpec("fastapi_modulo.modulos.proyectando.controladores.presupuesto", include_kwargs={"prefix": "/proyectando"}),
            RouterSpec("fastapi_modulo.modulos.proyectando.controladores.tablero"),
            RouterSpec("fastapi_modulo.modulos.proyectando.controladores.datos_preliminares"),
            RouterSpec("fastapi_modulo.modulos.proyectando.controladores.crecimiento_general"),
            RouterSpec("fastapi_modulo.modulos.proyectando.controladores.sucursales"),
            RouterSpec("fastapi_modulo.modulos.proyectando.controladores.no_acceso"),
        ],
    ),
    ModuleDefinition(
        key="mesa_control",
        label="Mesa de control",
        description="Control ejecutivo consolidado.",
        route="/mesa-de-control",
        icon="fa-solid fa-gauge-high",
        app_access_name="Mesa de control",
        sidebar_visible=True,
        manageable=True,
        boot_strategy="builtin",
        router_specs=[
            RouterSpec("fastapi_modulo.modulos.mesa_control.controladores.mesa_control"),
        ],
    ),
    ModuleDefinition(
        key="cartera_prestamos",
        label="Cartera de préstamos",
        description="Resumen ejecutivo de cartera.",
        route="/resumen_ejecutivo",
        icon="fa-solid fa-hand-holding-dollar",
        manifest_file="fastapi_modulo/modulos/cartera_prestamos/__manifest__.py",
        app_access_name="Cartera de préstamos",
        sidebar_visible=True,
        manageable=True,
        boot_strategy="builtin",
        router_specs=[
            RouterSpec("fastapi_modulo.modulos.cartera_prestamos.controladores.cartera_prestamos"),
        ],
    ),
    ModuleDefinition(
        key="pld",
        label="PLD",
        description="Prevención de lavado de dinero.",
        route="/pld",
        icon="fa-solid fa-shield-halved",
        app_access_name="PLD",
        sidebar_visible=True,
        manageable=True,
        boot_strategy="builtin",
        router_specs=[RouterSpec("fastapi_modulo.modulos.pld.controladores.pld")],
    ),
    ModuleDefinition(
        key="mkt",
        label="MKT",
        description="Marketing y comunicación.",
        route="/mkt/digital",
        icon="fa-solid fa-bullhorn",
        app_access_name="MKT",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.mkt.controladores.mkt")],
    ),
    ModuleDefinition(
        key="intelicoop",
        label="Intelicoop",
        description="Analítica e inteligencia institucional.",
        route="/inicio/intelicoop",
        icon="fa-solid fa-microchip",
        app_access_name="Intelicoop",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.intelicoop.controladores.intelicoop")],
    ),
    ModuleDefinition(
        key="brujula",
        label="Brújula",
        description="Seguimiento visual de indicadores y objetivos.",
        route="/brujula",
        icon="fa-regular fa-compass",
        app_access_name="Brújula",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.brujula.controladores.brujula")],
    ),
    ModuleDefinition(
        key="crm",
        label="CRM",
        description="Gestión comercial y de relaciones.",
        route="/crm",
        icon="fa-solid fa-address-card",
        app_access_name="CRM",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.crm.controladores.crm")],
    ),
    ModuleDefinition(
        key="encuestas",
        label="Encuestas",
        description="Campañas, constructor, respuesta y resultados.",
        route="/encuestas",
        icon="fa fa-square-poll-vertical",
        metadata_file="fastapi_modulo/modulos/encuestas/modulo.json",
        app_access_name="Encuestas",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.encuestas.controladores.encuesta")],
    ),
    ModuleDefinition(
        key="auditoria",
        label="Auditoría",
        description="Hallazgos, seguimiento y control de auditoría.",
        route="/auditoria",
        icon="fa-solid fa-clipboard-check",
        app_access_name="Auditoria",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.auditoria.controladores.auditoria")],
    ),
    ModuleDefinition(
        key="activo_fijo",
        label="Gestión de Activo Fijo",
        description="Inventario y control de activos fijos.",
        route="/activo-fijo",
        icon="fa-solid fa-building-columns",
        app_access_name="ActivoFijo",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.activo_fijo.controladores.activo_fijo")],
    ),
    ModuleDefinition(
        key="bsc",
        label="BSC",
        description="Tablero principal institucional.",
        route="/inicio",
        icon="fa-regular fa-circle-dot",
        app_access_name="BSC",
        sidebar_visible=True,
        manageable=True,
        boot_strategy="builtin",
    ),
    ModuleDefinition(
        key="control_seguimiento",
        label="Control y seguimiento",
        description="Programa, evidencias, hallazgos y reportes.",
        route="/control-seguimiento",
        icon="fa-solid fa-list-check",
        manifest_file="fastapi_modulo/modulos/control_interno/__manifest__.py",
        app_access_name="Control y seguimiento",
        sidebar_visible=True,
        manageable=True,
        router_specs=[
            RouterSpec("fastapi_modulo.modulos.control_interno.controladores.control"),
            RouterSpec("fastapi_modulo.modulos.control_interno.controladores.programa"),
            RouterSpec("fastapi_modulo.modulos.control_interno.controladores.evidencia"),
            RouterSpec("fastapi_modulo.modulos.control_interno.controladores.hallazgos"),
            RouterSpec("fastapi_modulo.modulos.control_interno.controladores.tablero"),
            RouterSpec("fastapi_modulo.modulos.control_interno.controladores.reportes_ci"),
        ],
    ),
    ModuleDefinition(
        key="kpis",
        label="KPIs",
        description="Indicadores clave y analítica resumida.",
        route="/kpis",
        icon="fa-solid fa-chart-line",
        app_access_name="KPIs",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.kpis.controladores.kpis")],
    ),
    ModuleDefinition(
        key="reportes",
        label="Reportes",
        description="Generación y consulta de reportes.",
        route="/reportes",
        icon="fa-regular fa-file-lines",
        app_access_name="Reportes",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("reportes.controladores.reportes")],
    ),
    ModuleDefinition(
        key="empresa",
        label="Empresa",
        description="Configuración institucional y estructura MAIN.",
        route="/identidad-institucional",
        icon="fa-solid fa-building",
        app_access_name="Empresa",
        sidebar_visible=True,
        manageable=True,
        boot_strategy="builtin",
        router_specs=[
            RouterSpec("fastapi_modulo.modulos.identidad_institucional.controladores.identidad_institucional"),
        ],
    ),
    ModuleDefinition(
        key="capacitacion",
        label="Capacitación",
        description="Cursos, presentaciones y evaluaciones.",
        route="/capacitacion",
        icon="fa-solid fa-graduation-cap",
        metadata_file="fastapi_modulo/modulos/capacitacion/modulo.json",
        app_access_name="Capacitacion",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.capacitacion.controladores.capacitacion")],
    ),
    ModuleDefinition(
        key="multiempresa",
        label="Multiempresa",
        description="Gestión y aislamiento por empresa.",
        route="/multiempresa",
        icon="fa-solid fa-layer-group",
        app_access_name="Multiempresa",
        sidebar_visible=True,
        manageable=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.multiempresa.controladores.multiempresa")],
    ),
    ModuleDefinition(
        key="system_admin",
        label="Módulos",
        description="Activación y desactivación global de módulos.",
        route="/modulos",
        icon="fa-solid fa-cubes",
        sidebar_visible=False,
        manageable=False,
        always_enabled=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.sistema.modulos_admin")],
    ),
    ModuleDefinition(
        key="personalizacion_core",
        label="Personalización",
        description="Core de personalización institucional.",
        sidebar_visible=False,
        manageable=False,
        always_enabled=True,
        router_specs=[RouterSpec("fastapi_modulo.personalizacion", attr_name="personalizacion_router")],
    ),
    ModuleDefinition(
        key="membresia_core",
        label="Membresía",
        description="Core de membresía.",
        sidebar_visible=False,
        manageable=False,
        always_enabled=True,
        router_specs=[RouterSpec("fastapi_modulo.membresia", attr_name="membresia_router")],
    ),
    ModuleDefinition(
        key="roles_core",
        label="Roles",
        description="Core de roles y permisos.",
        sidebar_visible=False,
        manageable=False,
        always_enabled=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.personalizacion.controladores.roles")],
    ),
    ModuleDefinition(
        key="plantillas_core",
        label="Plantillas",
        description="Core de plantillas.",
        sidebar_visible=False,
        manageable=False,
        always_enabled=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.plantillas.controladores.plantillas_forms")],
    ),
    ModuleDefinition(
        key="diagnostico_core",
        label="Diagnóstico",
        description="Core de diagnóstico.",
        sidebar_visible=False,
        manageable=False,
        always_enabled=True,
        router_specs=[RouterSpec("fastapi_modulo.modulos.diagnostico.controladores.diagnostico")],
    ),
    ModuleDefinition(
        key="ajustes_ia_core",
        label="Ajustes IA",
        description="Configuración de IA.",
        sidebar_visible=False,
        manageable=False,
        always_enabled=True,
        router_specs=[RouterSpec("fastapi_modulo.ajustes_ia")],
    ),
    ModuleDefinition(
        key="ia_core",
        label="IA",
        description="Router agregado de IA.",
        sidebar_visible=False,
        manageable=False,
        always_enabled=True,
        router_specs=[
            RouterSpec("fastapi_modulo.modulos.ia.controladores.ia_router", attr_name="ia_router"),
            RouterSpec("fastapi_modulo.modulos.ia.controladores.predictivo"),
        ],
    ),
]

MODULES_BY_KEY = {module.key: module for module in MODULE_DEFINITIONS}
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APP_ACCESS_TO_MODULE = {
    module.app_access_name: module
    for module in MODULE_DEFINITIONS
    if module.app_access_name
}


def list_system_app_access_options() -> List[str]:
    return [module.app_access_name for module in MODULE_DEFINITIONS if module.app_access_name]


def _ensure_module_settings_table() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS system_module_settings (
                    module_key VARCHAR(120) PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        for module in MODULE_DEFINITIONS:
            conn.execute(
                text(
                    """
                    INSERT INTO system_module_settings (module_key, enabled, updated_at)
                    SELECT :module_key, :enabled, :updated_at
                    WHERE NOT EXISTS (
                        SELECT 1 FROM system_module_settings WHERE module_key = :module_key
                    )
                    """
                ),
                {
                    "module_key": module.key,
                    "enabled": 1 if (module.default_enabled or module.always_enabled) else 0,
                    "updated_at": datetime.utcnow(),
                },
            )


def _read_module_state_map() -> Dict[str, bool]:
    _ensure_module_settings_table()
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT module_key, enabled FROM system_module_settings")).mappings().all()
    return {str(row["module_key"]): bool(row["enabled"]) for row in rows}


def is_module_enabled(module_key: str) -> bool:
    module = MODULES_BY_KEY.get(str(module_key or "").strip())
    if not module:
        return True
    if module.always_enabled:
        return True
    states = _read_module_state_map()
    return bool(states.get(module.key, module.default_enabled))


def is_app_access_enabled(app_access_name: str) -> bool:
    module = APP_ACCESS_TO_MODULE.get(str(app_access_name or "").strip())
    if not module:
        return True
    return is_module_enabled(module.key)


def get_active_module_keys() -> List[str]:
    return [module.key for module in MODULE_DEFINITIONS if is_module_enabled(module.key)]


def get_active_app_access_names() -> List[str]:
    return [
        module.app_access_name
        for module in MODULE_DEFINITIONS
        if module.app_access_name and is_module_enabled(module.key)
    ]


def _load_module_metadata(module: ModuleDefinition) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}

    metadata_file = str(module.metadata_file or "").strip()
    if metadata_file:
        file_path = os.path.abspath(os.path.join(_PROJECT_ROOT, metadata_file))
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as fh:
                    raw_payload = json.load(fh)
                if isinstance(raw_payload, dict):
                    payload.update(raw_payload)
            except Exception:
                pass

    manifest_file = str(module.manifest_file or "").strip()
    if manifest_file:
        file_path = os.path.abspath(os.path.join(_PROJECT_ROOT, manifest_file))
        if os.path.exists(file_path):
            try:
                spec = spec_from_file_location(f"{module.key}__manifest__", file_path)
                if spec and spec.loader:
                    manifest_module = module_from_spec(spec)
                    spec.loader.exec_module(manifest_module)
                    manifest_payload = getattr(manifest_module, "MANIFEST", {})
                    if isinstance(manifest_payload, dict):
                        payload["manifest"] = manifest_payload
            except Exception:
                pass

    return payload


def _resolve_manifest_icon_url(metadata: Dict[str, Any]) -> str:
    manifest = metadata.get("manifest") if isinstance(metadata, dict) else {}
    if not isinstance(manifest, dict):
        return ""
    assets = manifest.get("assets")
    if not isinstance(assets, dict):
        return ""
    static_base_url = str(assets.get("static_base_url") or "").strip().rstrip("/")
    if not static_base_url:
        return ""
    for key in ("img", "description"):
        entries = assets.get(key)
        if not isinstance(entries, list):
            continue
        for item in entries:
            path = str(item or "").strip().lstrip("/")
            if not path:
                continue
            if path.startswith("static/"):
                path = path[len("static/"):]
            return f"{static_base_url}/{path}"
    return ""


def list_modules_payload() -> List[Dict[str, Any]]:
    states = _read_module_state_map()
    payload: List[Dict[str, Any]] = []
    for module in MODULE_DEFINITIONS:
        metadata = _load_module_metadata(module)
        payload.append(
            {
                "key": module.key,
                "label": str(metadata.get("label") or metadata.get("manifest", {}).get("label") or module.label),
                "description": str(metadata.get("description") or metadata.get("manifest", {}).get("description") or module.description),
                "route": str(metadata.get("route") or metadata.get("manifest", {}).get("route") or module.route),
                "icon": str(metadata.get("icon") or module.icon),
                "icon_url": _resolve_manifest_icon_url(metadata),
                "app_access_name": module.app_access_name,
                "sidebar_visible": module.sidebar_visible,
                "manageable": module.manageable,
                "always_enabled": module.always_enabled,
                "default_enabled": module.default_enabled,
                "enabled": True if module.always_enabled else bool(states.get(module.key, module.default_enabled)),
                "boot_strategy": module.boot_strategy,
                "router_count": len(module.router_specs),
            }
        )
    return payload


def set_module_enabled(module_key: str, enabled: bool) -> Dict[str, Any]:
    module = MODULES_BY_KEY.get(str(module_key or "").strip())
    if not module:
        raise KeyError("Módulo no encontrado.")
    if module.always_enabled or not module.manageable:
        raise ValueError("Este módulo no se puede desactivar.")
    _ensure_module_settings_table()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE system_module_settings
                SET enabled = :enabled,
                    updated_at = :updated_at
                WHERE module_key = :module_key
                """
            ),
            {
                "enabled": 1 if enabled else 0,
                "updated_at": datetime.utcnow(),
                "module_key": module.key,
            },
        )
    result = next(item for item in list_modules_payload() if item["key"] == module.key)
    result["restart_required"] = True
    return result


def register_enabled_routers(app: FastAPI, phase: str = "startup") -> List[str]:
    _ensure_module_settings_table()
    registered: List[str] = []
    for module in MODULE_DEFINITIONS:
        if module.registration_phase != phase:
            continue
        if not module.router_specs or not is_module_enabled(module.key):
            continue
        for spec in module.router_specs:
            imported = import_module(spec.module_path)
            router = getattr(imported, spec.attr_name)
            app.include_router(router, **(spec.include_kwargs or {}))
        registered.append(module.key)
    return registered


def iter_manageable_modules() -> Iterable[ModuleDefinition]:
    return (module for module in MODULE_DEFINITIONS if module.manageable)
