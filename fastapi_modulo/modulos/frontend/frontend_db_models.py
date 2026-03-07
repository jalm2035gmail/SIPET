from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text

from fastapi_modulo.db import Base


class FrontendPage(Base):
    __tablename__ = "frontend_pages"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False, default="")
    slug = Column(String, nullable=False, unique=True, index=True, default="")
    status = Column(String, nullable=False, default="draft", index=True)
    is_home = Column(Boolean, default=False, nullable=False)
    gjs_html = Column(Text, default="", nullable=False)
    gjs_css = Column(Text, default="", nullable=False)
    blocks = Column(JSON, default=list, nullable=False)
    meta = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class FrontendPageVersion(Base):
    __tablename__ = "frontend_page_versions"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False, default="")
    status = Column(String, nullable=False, default="draft")
    gjs_html = Column(Text, default="", nullable=False)
    gjs_css = Column(Text, default="", nullable=False)
    meta = Column(JSON, default=dict, nullable=False)
    saved_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
