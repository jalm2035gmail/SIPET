from fastapi import APIRouter, Depends, HTTPException
from typing import List
from app.schemas.strategic import StrategicPlanCreate, StrategicPlanResponse
from app.services.strategic_service import StrategicService

router = APIRouter(prefix="/strategic", tags=["strategic"])

@router.post("/plans/", response_model=StrategicPlanResponse)
async def create_strategic_plan(
    plan: StrategicPlanCreate,
    service: StrategicService = Depends()
):
    """Crear un nuevo plan estratégico"""
    return await service.create_strategic_plan(plan)

@router.get("/plans/", response_model=List[StrategicPlanResponse])
async def get_strategic_plans(
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    service: StrategicService = Depends()
):
    """Obtener todos los planes estratégicos"""
    return await service.get_strategic_plans(status, skip, limit)

@router.post("/plans/{plan_id}/diagnostic/")
async def create_diagnostic_analysis(
    plan_id: int,
    diagnostic_data: dict,
    service: StrategicService = Depends()
):
    """Agregar análisis de diagnóstico a un plan"""
    return await service.add_diagnostic_analysis(plan_id, diagnostic_data)

@router.post("/plans/{plan_id}/generate-poa/{year}")
async def generate_poa_from_strategic_plan(
    plan_id: int,
    year: int,
    service: StrategicService = Depends()
):
    """Generar POA a partir del plan estratégico"""
    return await service.generate_poa(plan_id, year)
