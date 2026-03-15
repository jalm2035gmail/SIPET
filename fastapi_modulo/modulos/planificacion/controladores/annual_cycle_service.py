from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Body, Request
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text


router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_ROOT = PROJECT_ROOT / "runtime" / "annual_cycles"
ARCHIVE_ROOT = RUNTIME_ROOT / "archives"
STORAGE_ROOT = RUNTIME_ROOT / "storage"
MODULE_KEY = "poa_presupuesto"

LEGACY_PRESUPUESTO_TXT_PATH = PROJECT_ROOT / "presupuesto.txt"
LEGACY_CONTROL_MENSUAL_STORE_PATH = (
    PROJECT_ROOT / "fastapi_modulo" / "modulos" / "proyectando" / "control_mensual_store.json"
)
LEGACY_CONTROL_MENSUAL_ALT_PATH = (
    PROJECT_ROOT / "fastapi_modulo" / "modulos" / "presupuesto" / "control_mensual_store.json"
)


def _bind_core_symbols() -> None:
    from fastapi_modulo import main as core

    globals()["SessionLocal"] = getattr(core, "SessionLocal")
    globals()["_normalize_tenant_id"] = getattr(core, "_normalize_tenant_id")
    globals()["get_current_tenant"] = getattr(core, "get_current_tenant")


def _sanitize_tenant_slug(tenant_id: str) -> str:
    raw = str(tenant_id or "default").strip().lower()
    safe = re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-")
    return safe or "default"


def _normalize_year(raw_value: Any) -> int:
    try:
        year = int(str(raw_value or "").strip())
    except (TypeError, ValueError):
        year = 0
    if year < 2000 or year > 3000:
        year = 0
    return year


def _ensure_cycle_tables(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tenant_operational_cycles (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              tenant_id VARCHAR(120) NOT NULL,
              module_key VARCHAR(120) NOT NULL,
              active_year INTEGER NOT NULL,
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    db.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_tenant_operational_cycles "
            "ON tenant_operational_cycles(tenant_id, module_key)"
        )
    )


def _ensure_strategy_year_columns(db, fallback_year: int | None = None) -> None:
    fallback = int(fallback_year or datetime.now().year)
    stmts = [
        (
            "strategic_axes_config",
            [
                "ALTER TABLE strategic_axes_config ADD COLUMN fiscal_year INTEGER",
                (
                    "UPDATE strategic_axes_config "
                    "SET fiscal_year = COALESCE("
                    "CAST(strftime('%Y', fecha_inicial) AS INTEGER), "
                    "CAST(strftime('%Y', fecha_final) AS INTEGER), "
                    f"{fallback}) "
                    "WHERE fiscal_year IS NULL OR fiscal_year = 0"
                ),
                "CREATE INDEX IF NOT EXISTS ix_strategic_axes_config_fiscal_year ON strategic_axes_config(fiscal_year)",
            ],
        ),
        (
            "strategic_objectives_config",
            [
                "ALTER TABLE strategic_objectives_config ADD COLUMN fiscal_year INTEGER",
                (
                    "UPDATE strategic_objectives_config "
                    "SET fiscal_year = COALESCE("
                    "CAST(strftime('%Y', fecha_inicial) AS INTEGER), "
                    "CAST(strftime('%Y', fecha_final) AS INTEGER), "
                    "(SELECT a.fiscal_year FROM strategic_axes_config a WHERE a.id = strategic_objectives_config.eje_id), "
                    f"{fallback}) "
                    "WHERE fiscal_year IS NULL OR fiscal_year = 0"
                ),
                "CREATE INDEX IF NOT EXISTS ix_strategic_objectives_config_fiscal_year ON strategic_objectives_config(fiscal_year)",
            ],
        ),
        (
            "poa_activities",
            [
                "ALTER TABLE poa_activities ADD COLUMN fiscal_year INTEGER",
                (
                    "UPDATE poa_activities "
                    "SET fiscal_year = COALESCE("
                    "CAST(strftime('%Y', fecha_inicial) AS INTEGER), "
                    "CAST(strftime('%Y', fecha_final) AS INTEGER), "
                    "(SELECT o.fiscal_year FROM strategic_objectives_config o WHERE o.id = poa_activities.objective_id), "
                    f"{fallback}) "
                    "WHERE fiscal_year IS NULL OR fiscal_year = 0"
                ),
                "CREATE INDEX IF NOT EXISTS ix_poa_activities_fiscal_year ON poa_activities(fiscal_year)",
            ],
        ),
        (
            "poa_subactivities",
            [
                "ALTER TABLE poa_subactivities ADD COLUMN fiscal_year INTEGER",
                (
                    "UPDATE poa_subactivities "
                    "SET fiscal_year = COALESCE("
                    "CAST(strftime('%Y', fecha_inicial) AS INTEGER), "
                    "CAST(strftime('%Y', fecha_final) AS INTEGER), "
                    "(SELECT a.fiscal_year FROM poa_activities a WHERE a.id = poa_subactivities.activity_id), "
                    f"{fallback}) "
                    "WHERE fiscal_year IS NULL OR fiscal_year = 0"
                ),
                "CREATE INDEX IF NOT EXISTS ix_poa_subactivities_fiscal_year ON poa_subactivities(fiscal_year)",
            ],
        ),
    ]
    for table_name, table_stmts in stmts:
        exists = db.execute(
            text(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name = :table_name"
            ),
            {"table_name": table_name},
        ).fetchone()
        if not exists:
            continue
        for stmt in table_stmts:
            try:
                db.execute(text(stmt))
            except Exception:
                continue


def _budget_year_dir(tenant_id: str, year: int) -> Path:
    return STORAGE_ROOT / _sanitize_tenant_slug(tenant_id) / str(int(year))


def get_presupuesto_txt_path(tenant_id: str, year: int) -> Path:
    return _budget_year_dir(tenant_id, year) / "presupuesto.txt"


def get_control_mensual_store_path(tenant_id: str, year: int) -> Path:
    return _budget_year_dir(tenant_id, year) / "control_mensual_store.json"


def _copy_if_missing(source: Path, destination: Path) -> None:
    if not source.exists() or destination.exists():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def ensure_budget_storage_for_year(tenant_id: str, year: int) -> None:
    year_dir = _budget_year_dir(tenant_id, year)
    year_dir.mkdir(parents=True, exist_ok=True)
    _copy_if_missing(LEGACY_PRESUPUESTO_TXT_PATH, get_presupuesto_txt_path(tenant_id, year))
    legacy_control_path = (
        LEGACY_CONTROL_MENSUAL_STORE_PATH
        if LEGACY_CONTROL_MENSUAL_STORE_PATH.exists()
        else LEGACY_CONTROL_MENSUAL_ALT_PATH
    )
    _copy_if_missing(legacy_control_path, get_control_mensual_store_path(tenant_id, year))


def _known_budget_years(tenant_id: str) -> set[int]:
    tenant_dir = STORAGE_ROOT / _sanitize_tenant_slug(tenant_id)
    years: set[int] = set()
    if tenant_dir.exists():
        for item in tenant_dir.iterdir():
            if not item.is_dir():
                continue
            year = _normalize_year(item.name)
            if year:
                years.add(year)
    return years


def list_known_operational_years(db, tenant_id: str) -> list[int]:
    years: set[int] = _known_budget_years(tenant_id)
    for table_name in (
        "strategic_axes_config",
        "strategic_objectives_config",
        "poa_activities",
        "poa_subactivities",
    ):
        try:
            rows = db.execute(
                text(
                    f"SELECT DISTINCT fiscal_year FROM {table_name} "
                    "WHERE tenant_id = :tenant_id AND fiscal_year IS NOT NULL AND fiscal_year > 0"
                ),
                {"tenant_id": tenant_id},
            ).fetchall()
        except Exception:
            rows = []
        for row in rows:
            year = _normalize_year(row[0] if row else 0)
            if year:
                years.add(year)
    if LEGACY_PRESUPUESTO_TXT_PATH.exists() or LEGACY_CONTROL_MENSUAL_STORE_PATH.exists() or LEGACY_CONTROL_MENSUAL_ALT_PATH.exists():
        years.add(datetime.now().year)
    if not years:
        years.add(datetime.now().year)
    return sorted(years)


def get_active_operational_year(db, tenant_id: str) -> int:
    _ensure_cycle_tables(db)
    known_years = list_known_operational_years(db, tenant_id)
    default_year = max(known_years) if known_years else datetime.now().year
    row = db.execute(
        text(
            "SELECT active_year FROM tenant_operational_cycles "
            "WHERE tenant_id = :tenant_id AND module_key = :module_key"
        ),
        {"tenant_id": tenant_id, "module_key": MODULE_KEY},
    ).fetchone()
    year = _normalize_year(row[0] if row else 0)
    if year:
        ensure_budget_storage_for_year(tenant_id, year)
        return year
    db.execute(
        text(
            "INSERT INTO tenant_operational_cycles (tenant_id, module_key, active_year, updated_at) "
            "VALUES (:tenant_id, :module_key, :active_year, CURRENT_TIMESTAMP)"
        ),
        {"tenant_id": tenant_id, "module_key": MODULE_KEY, "active_year": int(default_year)},
    )
    ensure_budget_storage_for_year(tenant_id, int(default_year))
    return int(default_year)


def set_active_operational_year(db, tenant_id: str, year: int) -> int:
    year = _normalize_year(year) or datetime.now().year
    _ensure_cycle_tables(db)
    db.execute(
        text(
            "INSERT INTO tenant_operational_cycles (tenant_id, module_key, active_year, updated_at) "
            "VALUES (:tenant_id, :module_key, :active_year, CURRENT_TIMESTAMP) "
            "ON CONFLICT(tenant_id, module_key) DO UPDATE SET "
            "active_year = excluded.active_year, updated_at = CURRENT_TIMESTAMP"
        ),
        {"tenant_id": tenant_id, "module_key": MODULE_KEY, "active_year": int(year)},
    )
    ensure_budget_storage_for_year(tenant_id, int(year))
    return int(year)


def _fetch_rows(db, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        rows = db.execute(text(sql), params).mappings().all()
    except Exception:
        return []
    return [dict(row) for row in rows]


def _build_year_snapshot(db, tenant_id: str, year: int) -> dict[str, Any]:
    axes = _fetch_rows(
        db,
        "SELECT * FROM strategic_axes_config WHERE tenant_id = :tenant_id AND fiscal_year = :year ORDER BY orden ASC, id ASC",
        {"tenant_id": tenant_id, "year": int(year)},
    )
    objectives = _fetch_rows(
        db,
        "SELECT * FROM strategic_objectives_config WHERE tenant_id = :tenant_id AND fiscal_year = :year ORDER BY orden ASC, id ASC",
        {"tenant_id": tenant_id, "year": int(year)},
    )
    activities = _fetch_rows(
        db,
        "SELECT * FROM poa_activities WHERE tenant_id = :tenant_id AND fiscal_year = :year ORDER BY id ASC",
        {"tenant_id": tenant_id, "year": int(year)},
    )
    subactivities = _fetch_rows(
        db,
        "SELECT * FROM poa_subactivities WHERE tenant_id = :tenant_id AND fiscal_year = :year ORDER BY nivel ASC, id ASC",
        {"tenant_id": tenant_id, "year": int(year)},
    )
    objective_ids = [int(item.get("id") or 0) for item in objectives if int(item.get("id") or 0) > 0]
    activity_ids = [int(item.get("id") or 0) for item in activities if int(item.get("id") or 0) > 0]
    snapshot = {
        "generated_at": datetime.utcnow().isoformat(),
        "tenant_id": tenant_id,
        "year": int(year),
        "axes": axes,
        "objectives": objectives,
        "activities": activities,
        "subactivities": subactivities,
        "objective_milestones": [],
        "activity_budgets": [],
        "activity_kpis": [],
        "activity_deliverables": [],
        "activity_milestone_links": [],
        "deliverable_approvals": [],
    }
    if objective_ids:
        placeholders = ", ".join(f":oid_{idx}" for idx, _ in enumerate(objective_ids))
        objective_params = {f"oid_{idx}": value for idx, value in enumerate(objective_ids)}
        snapshot["objective_milestones"] = _fetch_rows(
            db,
            f"SELECT * FROM strategic_objective_milestones WHERE objective_id IN ({placeholders}) ORDER BY objective_id ASC, orden ASC, id ASC",
            objective_params,
        )
        snapshot["deliverable_approvals"] = _fetch_rows(
            db,
            f"SELECT * FROM poa_deliverable_approvals WHERE objective_id IN ({placeholders}) ORDER BY created_at ASC, id ASC",
            objective_params,
        )
    if activity_ids:
        placeholders = ", ".join(f":aid_{idx}" for idx, _ in enumerate(activity_ids))
        activity_params = {f"aid_{idx}": value for idx, value in enumerate(activity_ids)}
        snapshot["activity_budgets"] = _fetch_rows(
            db,
            f"SELECT * FROM poa_activity_budgets WHERE activity_id IN ({placeholders}) ORDER BY activity_id ASC, orden ASC, id ASC",
            activity_params,
        )
        snapshot["activity_kpis"] = _fetch_rows(
            db,
            f"SELECT * FROM poa_activity_kpis WHERE activity_id IN ({placeholders}) ORDER BY activity_id ASC, orden ASC, id ASC",
            activity_params,
        )
        snapshot["activity_deliverables"] = _fetch_rows(
            db,
            f"SELECT * FROM poa_activity_deliverables WHERE activity_id IN ({placeholders}) ORDER BY activity_id ASC, orden ASC, id ASC",
            activity_params,
        )
        snapshot["activity_milestone_links"] = _fetch_rows(
            db,
            f"SELECT * FROM poa_activity_milestone_links WHERE activity_id IN ({placeholders}) ORDER BY activity_id ASC, orden ASC, id ASC",
            activity_params,
        )
    return snapshot


def get_archive_path(tenant_id: str, year: int) -> Path:
    archive_dir = ARCHIVE_ROOT / _sanitize_tenant_slug(tenant_id)
    archive_dir.mkdir(parents=True, exist_ok=True)
    return archive_dir / f"{int(year)}.zip"


def archive_operational_year(db, tenant_id: str, year: int) -> Path:
    archive_path = get_archive_path(tenant_id, year)
    snapshot = _build_year_snapshot(db, tenant_id, year)
    budget_path = get_presupuesto_txt_path(tenant_id, year)
    control_path = get_control_mensual_store_path(tenant_id, year)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr(
            "manifest.json",
            json.dumps(
                {
                    "tenant_id": tenant_id,
                    "year": int(year),
                    "created_at": datetime.utcnow().isoformat(),
                    "module_key": MODULE_KEY,
                },
                ensure_ascii=False,
                indent=2,
            ),
        )
        zip_file.writestr("poa/snapshot.json", json.dumps(snapshot, ensure_ascii=False, indent=2, default=str))
        if budget_path.exists():
            zip_file.write(budget_path, arcname="presupuesto/presupuesto.txt")
        if control_path.exists():
            zip_file.write(control_path, arcname="presupuesto/control_mensual_store.json")
    return archive_path


def start_new_operational_year(db, tenant_id: str, new_year: int) -> dict[str, Any]:
    new_year = _normalize_year(new_year)
    if not new_year:
        raise ValueError("Debes indicar un año válido.")
    current_year = get_active_operational_year(db, tenant_id)
    ensure_budget_storage_for_year(tenant_id, current_year)
    if new_year == current_year:
        archive_path = archive_operational_year(db, tenant_id, current_year)
        return {
            "active_year": current_year,
            "previous_year": current_year,
            "archive_path": archive_path,
            "changed": False,
        }
    archive_path = archive_operational_year(db, tenant_id, current_year)
    current_budget_path = get_presupuesto_txt_path(tenant_id, current_year)
    target_budget_path = get_presupuesto_txt_path(tenant_id, new_year)
    if current_budget_path.exists() and not target_budget_path.exists():
        target_budget_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(current_budget_path, target_budget_path)
    target_control_path = get_control_mensual_store_path(tenant_id, new_year)
    if not target_control_path.exists():
        target_control_path.parent.mkdir(parents=True, exist_ok=True)
        target_control_path.write_text(
            json.dumps({"rows": [], "updated_at": ""}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    set_active_operational_year(db, tenant_id, new_year)
    return {
        "active_year": new_year,
        "previous_year": current_year,
        "archive_path": archive_path,
        "changed": True,
    }


def get_cycle_context(db, tenant_id: str) -> dict[str, Any]:
    active_year = get_active_operational_year(db, tenant_id)
    years = list_known_operational_years(db, tenant_id)
    if active_year not in years:
        years.append(active_year)
    years = sorted(set(years))
    archives = []
    archive_dir = ARCHIVE_ROOT / _sanitize_tenant_slug(tenant_id)
    if archive_dir.exists():
        for item in sorted(archive_dir.glob("*.zip")):
            year = _normalize_year(item.stem)
            if not year:
                continue
            archives.append(
                {
                    "year": year,
                    "filename": item.name,
                    "download_url": f"/api/annual-cycle/archive/{year}",
                }
            )
    return {
        "active_year": active_year,
        "years": years,
        "archives": archives,
        "next_year_suggestion": max(years) + 1 if years else active_year + 1,
    }


def _current_tenant_id(request: Request) -> str:
    _bind_core_symbols()
    return _normalize_tenant_id(get_current_tenant(request))


@router.get("/api/annual-cycle/context")
def annual_cycle_context(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        _ensure_cycle_tables(db)
        _ensure_strategy_year_columns(db)
        payload = get_cycle_context(db, tenant_id)
        db.commit()
        return JSONResponse({"success": True, "data": payload})
    finally:
        db.close()


@router.post("/api/annual-cycle/start")
def annual_cycle_start(request: Request, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        _ensure_cycle_tables(db)
        _ensure_strategy_year_columns(db)
        result = start_new_operational_year(db, tenant_id, data.get("year"))
        db.commit()
        payload = get_cycle_context(db, tenant_id)
        payload["started"] = result
        return JSONResponse({"success": True, "data": payload})
    except ValueError as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=400)
    finally:
        db.close()


@router.get("/api/annual-cycle/archive/{year}")
def annual_cycle_archive_download(request: Request, year: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        tenant_id = _current_tenant_id(request)
        _ensure_cycle_tables(db)
        _ensure_strategy_year_columns(db)
        archive_path = get_archive_path(tenant_id, year)
        if not archive_path.exists():
            archive_path = archive_operational_year(db, tenant_id, int(year))
            db.commit()
        return FileResponse(archive_path, media_type="application/zip", filename=archive_path.name)
    finally:
        db.close()
