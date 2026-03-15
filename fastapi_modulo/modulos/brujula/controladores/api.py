from __future__ import annotations

from fastapi import APIRouter, Request

from fastapi_modulo.modulos.brujula.modelos.schemas import (
    ApiSuccessEnvelope,
    IndicatorDefinitionOverrideUpdate,
    IndicatorMatrixResponse,
    IndicatorNotebookUpdate,
    IndicatorScenariosResponse,
)
from fastapi_modulo.modulos.brujula.servicios.indicator_service import (
    delete_indicator_definition_response,
    get_indicator_notebook_response,
    get_indicator_scenarios_response,
    import_indicator_definitions_response,
    list_indicator_definitions_response,
    save_indicator_definition_response,
    save_indicator_notebook_response,
)


router = APIRouter()


@router.get("/api/brujula/indicadores/notebook")
def get_brujula_indicator_notebook(request: Request) -> ApiSuccessEnvelope:
    return get_indicator_notebook_response(request)


@router.post("/api/brujula/indicadores/notebook")
def save_brujula_indicator_notebook(request: Request, data: IndicatorNotebookUpdate) -> ApiSuccessEnvelope:
    return save_indicator_notebook_response(request, data)


@router.get("/api/brujula/indicadores/definiciones")
def list_brujula_indicator_definitions(request: Request) -> ApiSuccessEnvelope:
    return list_indicator_definitions_response(request)


@router.get("/api/brujula/indicadores/escenario")
def get_brujula_indicator_scenarios(request: Request) -> ApiSuccessEnvelope:
    return get_indicator_scenarios_response(request)


@router.post("/api/brujula/indicadores/definicion")
def save_brujula_indicator_definition(request: Request, data: IndicatorDefinitionOverrideUpdate) -> ApiSuccessEnvelope:
    return save_indicator_definition_response(request, data)


@router.delete("/api/brujula/indicadores/definicion/{indicator_id}")
def delete_brujula_indicator_definition(indicator_id: int):
    return delete_indicator_definition_response()


@router.post("/api/brujula/indicadores/importar")
def import_brujula_indicator_definitions():
    return import_indicator_definitions_response()
