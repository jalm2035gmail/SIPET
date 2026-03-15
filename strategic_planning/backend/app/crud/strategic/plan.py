from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import asc, desc, func, or_, Float
from sqlalchemy.orm import Session

from app.crud.MAIN import CRUDMAIN
from app.models.strategic.plan import PlanStatus, StrategicPlan
from app.schemas.strategic.plan import (
    StrategicPlanCreate,
    StrategicPlanFilter,
    StrategicPlanUpdate,
)


class CRUDStrategicPlan(CRUDMAIN[StrategicPlan, StrategicPlanCreate, StrategicPlanUpdate]):
    """Operaciones CRUD avanzadas sobre StrategicPlan."""

    def __init__(self, model: type[StrategicPlan]):
        super().__init__(model)

    def get_by_code(self, db: Session, code: str) -> Optional[StrategicPlan]:
        """Obtiene un plan por su código único."""
        return db.query(StrategicPlan).filter(StrategicPlan.code == code).first()

    def get_multi_with_filters(
        self,
        db: Session,
        *,
        filter_obj: StrategicPlanFilter,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "created_at",
        order_dir: str = "desc",
    ) -> Tuple[List[StrategicPlan], int]:
        """Aplica filtros, ordenamiento y paginación."""
        query = db.query(StrategicPlan)

        if filter_obj.status:
            query = query.filter(StrategicPlan.status == filter_obj.status)

        if filter_obj.department_id:
            query = query.filter(StrategicPlan.department_id == filter_obj.department_id)

        if filter_obj.start_date_from:
            query = query.filter(StrategicPlan.start_date >= filter_obj.start_date_from)

        if filter_obj.start_date_to:
            query = query.filter(StrategicPlan.start_date <= filter_obj.start_date_to)

        if filter_obj.end_date_from:
            query = query.filter(StrategicPlan.end_date >= filter_obj.end_date_from)

        if filter_obj.end_date_to:
            query = query.filter(StrategicPlan.end_date <= filter_obj.end_date_to)

        if filter_obj.created_by:
            query = query.filter(StrategicPlan.created_by == filter_obj.created_by)

        if filter_obj.search:
            term = f"%{filter_obj.search}%"
            query = query.filter(
                or_(
                    StrategicPlan.name.ilike(term),
                    StrategicPlan.code.ilike(term),
                    StrategicPlan.description.ilike(term),
                )
            )

        if filter_obj.is_active is not None:
            query = query.filter(StrategicPlan.is_active == filter_obj.is_active)

        total = query.count()

        order_column = getattr(StrategicPlan, order_by, StrategicPlan.created_at)
        if order_dir == "asc":
            query = query.order_by(asc(order_column))
        else:
            query = query.order_by(desc(order_column))

        plans = query.offset(skip).limit(limit).all()

        return plans, total

    def create_with_owner(
        self,
        db: Session,
        *,
        obj_in: StrategicPlanCreate,
        user_id: int,
    ) -> StrategicPlan:
        """Crea un plan estratégico asociando al usuario creador."""
        db_obj = StrategicPlan(
            **obj_in.model_dump(),
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_with_owner(
        self,
        db: Session,
        *,
        db_obj: StrategicPlan,
        obj_in: StrategicPlanUpdate,
        user_id: int,
    ) -> StrategicPlan:
        """Actualiza el plan y registra al actualizador."""
        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id
        update_data["updated_at"] = datetime.utcnow()
        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def change_status(
        self,
        db: Session,
        *,
        db_obj: StrategicPlan,
        new_status: PlanStatus,
        user_id: int,
        approval_date: Optional[date] = None,
    ) -> StrategicPlan:
        """Cambia el estado y registra aprobaciones si aplica."""
        db_obj.status = new_status
        db_obj.updated_by = user_id
        db_obj.updated_at = datetime.utcnow()

        if new_status == PlanStatus.APPROVED:
            db_obj.approval_date = approval_date or date.today()
            db_obj.approval_by = user_id

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_active_plans(self, db: Session) -> List[StrategicPlan]:
        """Trae planes activos (estado y período)."""
        today = date.today()
        return (
            db.query(StrategicPlan)
            .filter(
                StrategicPlan.status == PlanStatus.ACTIVE,
                StrategicPlan.start_date <= today,
                StrategicPlan.end_date >= today,
                StrategicPlan.is_active == True,
            )
            .all()
        )

    def get_upcoming_plans(self, db: Session, days: int = 30) -> List[StrategicPlan]:
        """Planes que empezarán pronto."""
        today = date.today()
        target_date = today + timedelta(days=days)
        return (
            db.query(StrategicPlan)
            .filter(
                StrategicPlan.status.in_([PlanStatus.APPROVED, PlanStatus.DRAFT]),
                StrategicPlan.start_date.between(today, target_date),
                StrategicPlan.is_active == True,
            )
            .all()
        )

    def get_statistics(
        self,
        db: Session,
        department_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Resumen estadístico de planes."""
        query = db.query(StrategicPlan)
        if department_id:
            query = query.filter(StrategicPlan.department_id == department_id)

        status_stats = (
            db.query(StrategicPlan.status, func.count(StrategicPlan.id).label("count"))
            .group_by(StrategicPlan.status)
            .all()
        )

        dept_stats = (
            db.query(StrategicPlan.department_id, func.count(StrategicPlan.id).label("count"))
            .group_by(StrategicPlan.department_id)
            .all()
        )

        avg_progress = db.query(func.coalesce(func.avg(func.cast(0, Float)), 0.0)).scalar() or 0.0

        today = date.today()
        upcoming = (
            db.query(StrategicPlan)
            .filter(
                StrategicPlan.end_date.between(today, today + timedelta(days=90)),
                StrategicPlan.status == PlanStatus.ACTIVE,
            )
            .order_by(StrategicPlan.end_date)
            .limit(5)
            .all()
        )

        status_map = {stat.status.value: stat.count for stat in status_stats}

        return {
            "total": query.count(),
            "active": status_map.get("active", 0),
            "completed": status_map.get("completed", 0),
            "draft": status_map.get("draft", 0),
            "by_status": status_map,
            "by_department": {str(stat.department_id): stat.count for stat in dept_stats},
            "average_progress": round(avg_progress, 2),
            "upcoming_deadlines": [
                {
                    "id": plan.id,
                    "name": plan.name,
                    "end_date": plan.end_date,
                    "days_remaining": (plan.end_date - today).days,
                }
                for plan in upcoming
            ],
        }

    def count_by_creator(self, db: Session, creator_id: int) -> int:
        """Cuenta cuántos planes creó un usuario específico."""
        return (
            db.query(func.count(StrategicPlan.id))
            .filter(StrategicPlan.created_by == creator_id)
            .scalar()
            or 0
        )

    def duplicate_plan(
        self,
        db: Session,
        *,
        source_plan_id: int,
        new_name: str,
        new_code: str,
        user_id: int,
    ) -> StrategicPlan:
        """Duplica un plan estratégico con nueva metadata."""
        source_plan = self.get(db, id=source_plan_id)
        if not source_plan:
            raise ValueError("Plan fuente no encontrado")

        new_plan_data = {
            "name": new_name,
            "code": new_code,
            "description": f"Copia de {source_plan.name}",
            "version": "1.0",
            "start_date": date.today(),
            "end_date": source_plan.end_date,
            "vision": source_plan.vision,
            "mission": source_plan.mission,
            "values": source_plan.values,
            "department_id": source_plan.department_id,
            "status": PlanStatus.DRAFT,
        }

        new_plan = self.create_with_owner(
            db,
            obj_in=StrategicPlanCreate(**new_plan_data),
            user_id=user_id,
        )

        # TODO: duplicar ejes, diagnósticos y relaciones clave
        return new_plan


strategic_plan = CRUDStrategicPlan(StrategicPlan)
