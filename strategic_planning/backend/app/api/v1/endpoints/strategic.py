from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.crud.strategic.diagnostic import diagnostic_analysis
from app.crud.strategic.plan import strategic_plan
from app.services.notification_service import NotificationService
from app.schemas.response import ErrorResponse, PaginatedResponse, SuccessResponse
from app.schemas.strategic.plan import (
    PlanStatus,
    StrategicPlanCreate,
    StrategicPlanFilter,
    StrategicPlanList,
    StrategicPlanResponse,
    StrategicPlanStats,
    StrategicPlanUpdate,
)
from app.templates.api import ApiResponseTemplate
from app.templates.strategic import StrategicPlanTemplate
from app.core.permissions import (
    Permission,
    PermissionManager,
    ResourcePermissionChecker,
    ResourceScope,
    require_permission,
)
from app.crud.user import user as user_crud
from app.services.poa_service import POAService, get_poa_service

router = APIRouter(prefix="/strategic/plans", tags=["strategic"])


@router.get("/", response_model=PaginatedResponse[List[StrategicPlanList]])
async def list_strategic_plans(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.STRATEGIC_VIEW_PLANS)),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    start_date_from: Optional[date] = Query(None),
    start_date_to: Optional[date] = Query(None),
    order_by: str = Query("created_at"),
    order_dir: str = Query("desc"),
):
    """
    Lista planes estratégicos con paginación y filtros
    ✅ REQUIERE PERMISO: strategic:view_plans
    """
    try:
        filter_obj = StrategicPlanFilter(
            status=status,
            department_id=department_id,
            search=search,
            start_date_from=start_date_from,
            start_date_to=start_date_to,
        )

        scope = current_user.get("resource_scope", ResourceScope.GLOBAL)
        if scope == ResourceScope.DEPARTMENT:
            user_dept = current_user.get("department_id")
            if not user_dept:
                return ApiResponseTemplate.paginated(
                    data=[],
                    total=0,
                    skip=skip,
                    limit=limit,
                    metadata={"reason": "No tienes departamento asignado"},
                )
            filter_obj.department_id = user_dept
        elif scope == ResourceScope.OWN:
            filter_obj.created_by = current_user["id"]

        plans, total = strategic_plan.get_multi_with_filters(
            db,
            filter_obj=filter_obj,
            skip=skip,
            limit=limit,
            order_by=order_by,
            order_dir=order_dir,
        )

        plan_responses: List[Dict[str, Any]] = []
        for plan in plans:
            plan_responses.append(
                {
                    "id": plan.id,
                    "name": plan.name,
                    "code": plan.code,
                    "status": plan.status,
                    "start_date": plan.start_date,
                    "end_date": plan.end_date,
                    "progress": plan.get_progress(),
                    "axes_count": len(plan.strategic_axes),
                    "created_by_name": f"User {plan.created_by}",
                    "department_name": plan.department.name if plan.department else None,
                }
            )

        template_metadata = StrategicPlanTemplate.create_plan_response(
            {"plans": plan_responses},
            include_details=False,
            include_actions=False,
        )

        return ApiResponseTemplate.paginated(
            data=plan_responses,
            total=total,
            skip=skip,
            limit=limit,
            metadata={
                "filters": filter_obj.model_dump(exclude_none=True),
                "order": {"by": order_by, "direction": order_dir},
                "template": template_metadata,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar planes estratégicos: {exc}",
        )


@router.get("/{plan_id}", response_model=SuccessResponse[StrategicPlanResponse], responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}})
async def get_strategic_plan(
    plan_id: int = Path(..., description="ID del plan estratégico"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene un plan estratégico por ID
    """
    try:
        plan = strategic_plan.get(db, id=plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan estratégico no encontrado",
            )

        plan_data = {
            "id": plan.id,
            "name": plan.name,
            "code": plan.code,
            "description": plan.description,
            "version": plan.version,
            "start_date": plan.start_date,
            "end_date": plan.end_date,
            "vision": plan.vision,
            "mission": plan.mission,
            "values": plan.values,
            "status": plan.status,
            "department_id": plan.department_id,
            "parent_plan_id": plan.parent_plan_id,
            "created_at": plan.created_at,
            "updated_at": plan.updated_at,
            "is_active": plan.is_active,
            "created_by": plan.created_by,
            "updated_by": plan.updated_by,
            "approval_date": plan.approval_date,
            "approval_by": plan.approval_by,
            "progress": plan.get_progress(),
            "days_remaining": plan.get_days_remaining(),
            "is_active_period": plan.is_active_period(),
            "axes_count": len(plan.strategic_axes),
            "poas_count": len(plan.poas),
        }

        return ApiResponseTemplate.success(
            data=plan_data,
            message="Plan estratégico obtenido exitosamente",
            metadata={
                "breadcrumb": StrategicPlanTemplate.create_breadcrumb(plan_id, "detail"),
                "actions": StrategicPlanTemplate._get_plan_actions(plan_data),
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el plan estratégico: {exc}",
        )


@router.post("/", response_model=SuccessResponse[StrategicPlanResponse], status_code=status.HTTP_201_CREATED)
async def create_strategic_plan(
    plan_in: StrategicPlanCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Crea un nuevo plan estratégico
    """
    try:
        existing = strategic_plan.get_by_code(db, code=plan_in.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un plan con este código",
            )

        plan = strategic_plan.create_with_owner(
            db,
            obj_in=plan_in,
            user_id=current_user["id"],
        )

        plan_data = {
            "id": plan.id,
            "name": plan.name,
            "code": plan.code,
            "description": plan.description,
            "version": plan.version,
            "start_date": plan.start_date,
            "end_date": plan.end_date,
            "vision": plan.vision,
            "mission": plan.mission,
            "values": plan.values,
            "status": plan.status,
            "created_at": plan.created_at,
            "is_active": plan.is_active,
            "created_by": plan.created_by,
        }

        return ApiResponseTemplate.success(
            data=plan_data,
            message="Plan estratégico creado exitosamente",
            status_code=status.HTTP_201_CREATED,
            metadata={
                "next_actions": [
                    {"label": "Agregar Diagnóstico", "url": f"/strategic/plans/{plan.id}/diagnostic"},
                    {"label": "Definir Ejes", "url": f"/strategic/plans/{plan.id}/axes"},
                    {"label": "Generar POA", "url": f"/strategic/plans/{plan.id}/generate-poa"},
                ]
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el plan estratégico: {exc}",
        )


@router.put("/{plan_id}", response_model=SuccessResponse[StrategicPlanResponse], responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}})
async def update_strategic_plan(
    plan_id: int,
    plan_in: StrategicPlanUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Actualiza un plan estratégico existente
    """
    try:
        plan = strategic_plan.get(db, id=plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan estratégico no encontrado",
            )

        if plan.created_by != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para editar este plan",
            )

        if plan_in.code and plan_in.code != plan.code:
            existing = strategic_plan.get_by_code(db, code=plan_in.code)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe un plan con este código",
                )

        updated_plan = strategic_plan.update_with_owner(
            db,
            db_obj=plan,
            obj_in=plan_in,
            user_id=current_user["id"],
        )

        plan_data = {
            "id": updated_plan.id,
            "name": updated_plan.name,
            "code": updated_plan.code,
            "description": updated_plan.description,
            "version": updated_plan.version,
            "start_date": updated_plan.start_date,
            "end_date": updated_plan.end_date,
            "vision": updated_plan.vision,
            "mission": updated_plan.mission,
            "values": updated_plan.values,
            "status": updated_plan.status,
            "updated_at": updated_plan.updated_at,
            "updated_by": updated_plan.updated_by,
        }

        return ApiResponseTemplate.success(
            data=plan_data,
            message="Plan estratégico actualizado exitosamente",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el plan estratégico: {exc}",
        )


@router.delete("/{plan_id}", response_model=SuccessResponse)
async def delete_strategic_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Elimina un plan estratégico (eliminación lógica)
    """
    try:
        plan = strategic_plan.get(db, id=plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan estratégico no encontrado",
            )

        if plan.created_by != current_user["id"] and current_user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para eliminar este plan",
            )

        if plan.poas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar un plan con POAs generados",
            )

        plan.soft_delete()
        db.commit()

        return ApiResponseTemplate.success(
            message="Plan estratégico eliminado exitosamente",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el plan estratégico: {exc}",
        )


@router.post("/{plan_id}/change-status", response_model=SuccessResponse[StrategicPlanResponse])
async def change_plan_status(
    plan_id: int,
    new_status: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Cambia el estado de un plan estratégico
    """
    try:
        plan = strategic_plan.get(db, id=plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan estratégico no encontrado",
            )

        valid_transitions = {
            "draft": ["in_review", "cancelled"],
            "in_review": ["approved", "draft", "cancelled"],
            "approved": ["active", "cancelled"],
            "active": ["completed", "cancelled"],
            "completed": ["archived"],
            "archived": [],
            "cancelled": [],
        }

        current_status = plan.status.value
        if new_status not in valid_transitions.get(current_status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transición de estado no permitida: {current_status} -> {new_status}",
            )

        try:
            new_status_enum = PlanStatus(new_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estado inválido",
            )

        updated_plan = strategic_plan.change_status(
            db,
            db_obj=plan,
            new_status=new_status_enum,
            user_id=current_user["id"],
        )

        NotificationService.notify_plan_status_change(
            db=db,
            plan=updated_plan,
            new_status=new_status,
            triggered_by_id=current_user["id"],
        )

        plan_data = {
            "id": updated_plan.id,
            "name": updated_plan.name,
            "code": updated_plan.code,
            "status": updated_plan.status,
            "updated_at": updated_plan.updated_at,
        }

        return ApiResponseTemplate.success(
            data=plan_data,
            message=f"Estado del plan cambiado a {new_status}",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cambiar el estado del plan: {exc}",
        )


@router.post("/{plan_id}/generate-poa", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def generate_poa_from_plan(
    plan_id: int,
    year: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    poa_service: POAService = Depends(get_poa_service),
):
    try:
        plan = strategic_plan.get(db, id=plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plan estratégico no encontrado",
            )
        target_year = year or (plan.start_date.year if plan.start_date else date.today().year)
        poa = poa_service.generate_poa_from_plan(plan, target_year)
        return ApiResponseTemplate.success(
            data={"id": poa.id, "year": poa.year, "created_at": poa.created_at},
            message="POA generado a partir del plan estratégico",
            status_code=status.HTTP_201_CREATED,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar el POA: {exc}",
        )


@router.get("/{plan_id}/diagnostic", response_model=SuccessResponse, responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}})
async def get_plan_diagnostic(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene el análisis de diagnóstico de un plan
    """
    try:
        diagnostic = diagnostic_analysis.get_by_plan_id(db, plan_id=plan_id)
        if not diagnostic:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Análisis de diagnóstico no encontrado",
            )

        summary = diagnostic_analysis.get_summary(db, plan_id=plan_id)

        return ApiResponseTemplate.success(
            data={
                "diagnostic": {
                    "id": diagnostic.id,
                    "swot_matrix": diagnostic.get_swot_matrix(),
                    "pestel_categories": diagnostic.get_pestel_categories(),
                    "porter_forces": diagnostic.get_porter_forces(),
                    "key_findings": diagnostic.key_findings,
                    "created_at": diagnostic.created_at,
                },
                "summary": summary,
            },
            message="Análisis de diagnóstico obtenido exitosamente",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener el diagnóstico: {exc}",
        )


@router.get("/stats/overview", response_model=SuccessResponse[StrategicPlanStats])
async def get_plans_statistics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    department_id: Optional[int] = Query(None),
):
    """
    Obtiene estadísticas generales de planes estratégicos
    """
    try:
        stats = strategic_plan.get_statistics(db, department_id=department_id)

        return ApiResponseTemplate.success(
            data=stats,
            message="Estadísticas obtenidas exitosamente",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener estadísticas: {exc}",
        )
