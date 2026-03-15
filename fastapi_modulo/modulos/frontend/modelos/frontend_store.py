from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fastapi_modulo.db import MAIN, SessionLocal, engine
from fastapi_modulo.modulos.frontend.modelos.frontend_db_models import FrontendPage, FrontendPageVersion

_STORE_PATH = os.path.join("fastapi_modulo", "modulos", "frontend", "pages_store.json")
_VERSIONS_PATH = os.path.join("fastapi_modulo", "modulos", "frontend", "versions_store.json")
_MAX_VERSIONS = 5


def ensure_frontend_schema() -> None:
    MAIN.metadata.create_all(
        bind=engine,
        tables=[FrontendPage.__table__, FrontendPageVersion.__table__],
        checkfirst=True,
    )


def _db() -> Session:
    db = SessionLocal()
    _migrate_legacy_files_if_needed(db)
    return db


ensure_frontend_schema()


def _load_legacy_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, type(default)) else default
    except (OSError, json.JSONDecodeError):
        return default


def _page_dict(row: FrontendPage) -> Dict[str, Any]:
    return {
        "id": row.id,
        "title": row.title,
        "slug": row.slug,
        "status": row.status,
        "is_home": bool(row.is_home),
        "gjs_html": row.gjs_html or "",
        "gjs_css": row.gjs_css or "",
        "blocks": row.blocks if isinstance(row.blocks, list) else [],
        "meta": row.meta if isinstance(row.meta, dict) else {},
    }


def _version_dict(row: FrontendPageVersion) -> Dict[str, Any]:
    return {
        "saved_at": row.saved_at.strftime("%Y-%m-%d %H:%M UTC") if row.saved_at else "",
        "title": row.title,
        "status": row.status,
        "gjs_html": row.gjs_html or "",
        "gjs_css": row.gjs_css or "",
        "meta": row.meta if isinstance(row.meta, dict) else {},
    }


def _migrate_legacy_files_if_needed(db: Session) -> None:
    has_pages = db.query(FrontendPage.id).first() is not None
    if has_pages:
        return

    pages = _load_legacy_json(_STORE_PATH, [])
    versions = _load_legacy_json(_VERSIONS_PATH, {})
    if not pages:
        return

    for page in pages:
        row = FrontendPage(
            id=str(page.get("id") or ""),
            title=str(page.get("title") or "Sin título").strip(),
            slug=str(page.get("slug") or "").strip(),
            status=str(page.get("status") or "draft").strip(),
            is_home=bool(page.get("is_home", False)),
            gjs_html=str(page.get("gjs_html") or ""),
            gjs_css=str(page.get("gjs_css") or ""),
            blocks=page.get("blocks") if isinstance(page.get("blocks"), list) else [],
            meta=page.get("meta") if isinstance(page.get("meta"), dict) else {},
        )
        db.add(row)
        for snap in versions.get(row.id, [])[:_MAX_VERSIONS]:
            db.add(
                FrontendPageVersion(
                    page_id=row.id,
                    title=str(snap.get("title") or row.title),
                    status=str(snap.get("status") or row.status),
                    gjs_html=str(snap.get("gjs_html") or ""),
                    gjs_css=str(snap.get("gjs_css") or ""),
                    meta=snap.get("meta") if isinstance(snap.get("meta"), dict) else {},
                )
            )
    db.commit()


def list_pages() -> List[Dict[str, Any]]:
    db = _db()
    try:
        rows = db.query(FrontendPage).order_by(FrontendPage.created_at.asc(), FrontendPage.id.asc()).all()
        return [_page_dict(row) for row in rows]
    finally:
        db.close()


def get_page(page_id: str) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        row = db.query(FrontendPage).filter(FrontendPage.id == page_id).first()
        return _page_dict(row) if row else None
    finally:
        db.close()


def get_page_by_slug(slug: str, published_only: bool = False) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        q = db.query(FrontendPage).filter(FrontendPage.slug == slug)
        if published_only:
            q = q.filter(FrontendPage.status == "published")
        row = q.first()
        return _page_dict(row) if row else None
    finally:
        db.close()


def _snapshot_version(db: Session, page: FrontendPage) -> None:
    db.add(
        FrontendPageVersion(
            page_id=page.id,
            title=page.title,
            status=page.status,
            gjs_html=page.gjs_html or "",
            gjs_css=page.gjs_css or "",
            meta=page.meta if isinstance(page.meta, dict) else {},
        )
    )
    extra = (
        db.query(FrontendPageVersion)
        .filter(FrontendPageVersion.page_id == page.id)
        .order_by(FrontendPageVersion.saved_at.desc(), FrontendPageVersion.id.desc())
        .offset(_MAX_VERSIONS)
        .all()
    )
    for row in extra:
        db.delete(row)


def upsert_page(payload: Dict[str, Any]) -> Dict[str, Any]:
    db = _db()
    try:
        page_id = str(payload.get("id") or "").strip()
        row = db.query(FrontendPage).filter(FrontendPage.id == page_id).first() if page_id else None
        if row is None:
            row = FrontendPage(id=page_id)
            db.add(row)
        row.title = str(payload.get("title") or "Sin título").strip()
        row.slug = str(payload.get("slug") or "").strip()
        row.status = str(payload.get("status") or "draft").strip()
        row.is_home = bool(payload.get("is_home", False))
        row.gjs_html = str(payload.get("gjs_html") or "")
        row.gjs_css = str(payload.get("gjs_css") or "")
        row.blocks = payload.get("blocks") if isinstance(payload.get("blocks"), list) else []
        row.meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
        db.flush()
        if row.is_home:
            (
                db.query(FrontendPage)
                .filter(FrontendPage.id != row.id)
                .update({"is_home": False}, synchronize_session=False)
            )
        _snapshot_version(db, row)
        db.commit()
        db.refresh(row)
        pages = db.query(FrontendPage).order_by(FrontendPage.created_at.asc(), FrontendPage.id.asc()).all()
        return {"page": _page_dict(row), "pages": [_page_dict(item) for item in pages]}
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def delete_page(page_id: str) -> List[Dict[str, Any]]:
    db = _db()
    try:
        row = db.query(FrontendPage).filter(FrontendPage.id == page_id).first()
        if row:
            db.query(FrontendPageVersion).filter(FrontendPageVersion.page_id == row.id).delete()
            db.delete(row)
            db.commit()
        rows = db.query(FrontendPage).order_by(FrontendPage.created_at.asc(), FrontendPage.id.asc()).all()
        return [_page_dict(item) for item in rows]
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def publish_page(page_id: str) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        row = db.query(FrontendPage).filter(FrontendPage.id == page_id).first()
        if not row:
            return None
        row.status = "published"
        db.commit()
        db.refresh(row)
        return _page_dict(row)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()


def list_versions(page_id: str) -> List[Dict[str, Any]]:
    db = _db()
    try:
        rows = (
            db.query(FrontendPageVersion)
            .filter(FrontendPageVersion.page_id == page_id)
            .order_by(FrontendPageVersion.saved_at.desc(), FrontendPageVersion.id.desc())
            .all()
        )
        return [_version_dict(row) for row in rows]
    finally:
        db.close()


def restore_version(page_id: str, version_idx: int) -> Optional[Dict[str, Any]]:
    db = _db()
    try:
        page = db.query(FrontendPage).filter(FrontendPage.id == page_id).first()
        if not page:
            return None
        rows = (
            db.query(FrontendPageVersion)
            .filter(FrontendPageVersion.page_id == page_id)
            .order_by(FrontendPageVersion.saved_at.desc(), FrontendPageVersion.id.desc())
            .all()
        )
        if version_idx < 0 or version_idx >= len(rows):
            return None
        snap = rows[version_idx]
        page.gjs_html = snap.gjs_html or ""
        page.gjs_css = snap.gjs_css or ""
        page.meta = snap.meta if isinstance(snap.meta, dict) else {}
        db.commit()
        db.refresh(page)
        return _page_dict(page)
    except SQLAlchemyError:
        db.rollback()
        raise
    finally:
        db.close()
