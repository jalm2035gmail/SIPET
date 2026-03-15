from __future__ import annotations

import re
import secrets
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


NON_DATA_FIELD_TYPES = {"header", "paragraph", "html", "divider", "pagebreak"}


def slugify_value(value: str) -> str:
    MAIN = (value or "").strip().lower()
    MAIN = re.sub(r"[^a-z0-9]+", "-", MAIN)
    MAIN = re.sub(r"-+", "-", MAIN).strip("-")
    return MAIN or secrets.token_hex(4)


class FormFieldCreateSchema(BaseModel):
    field_type: str
    label: str
    name: str
    placeholder: Optional[str] = None
    help_text: Optional[str] = None
    default_value: Optional[str] = None
    is_required: bool = False
    validation_rules: Dict[str, Any] = Field(default_factory=dict)
    options: List[Dict[str, Any]] = Field(default_factory=list)
    order: int = 0
    conditional_logic: Dict[str, Any] = Field(default_factory=dict)


class FormDefinitionCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    slug: Optional[str] = None
    tenant_id: Optional[str] = None
    is_active: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    allowed_roles: List[str] = Field(default_factory=list)
    fields: List[FormFieldCreateSchema] = Field(default_factory=list)


class FormFieldResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    form_id: int
    field_type: str
    label: str
    name: str
    placeholder: Optional[str]
    help_text: Optional[str]
    default_value: Optional[str]
    is_required: bool
    validation_rules: Dict[str, Any]
    options: List[Dict[str, Any]]
    order: int
    conditional_logic: Dict[str, Any]


class FormDefinitionResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    tenant_id: str
    description: Optional[str]
    config: Dict[str, Any]
    allowed_roles: List[str]
    fields: List[FormFieldResponseSchema]
    is_active: bool
