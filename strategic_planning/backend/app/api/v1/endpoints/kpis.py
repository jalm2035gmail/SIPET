from fastapi import APIRouter, Depends
from app.schemas.kpis import KPIMeasurementCreate, ReportRequest
from app.services.kpi_service import KPIService
from app.services.report_service import ReportService

router = APIRouter(prefix="/kpis", tags=["kpis"])

@router.post("/{kpi_id}/measure")
async def record_kpi_measurement(
    kpi_id: int,
    measurement: KPIMeasurementCreate,
    service: KPIService = Depends()
):
    """Registrar medición de KPI"""
    return await service.record_measurement(kpi_id, measurement)

@router.get("/dashboard/strategic/{plan_id}")
async def get_strategic_dashboard(plan_id: int, service: ReportService = Depends()):
    """Dashboard del plan estratégico"""
    return await service.generate_strategic_dashboard(plan_id)

@router.post("/reports/generate")
async def generate_report(
    report_request: ReportRequest,
    service: ReportService = Depends()
):
    """Generar reporte personalizado"""
    return await service.generate_custom_report(report_request)
