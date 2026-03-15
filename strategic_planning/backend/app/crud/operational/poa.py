from datetime import date
from typing import List, Optional, Dict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.crud.MAIN import CRUDMAIN
from app.models.operational import POA
from app.schemas.operational.poa import POACreate, POAUpdate


class CRUDPOA(CRUDMAIN[POA, POACreate, POAUpdate]):
    """CRUD de POA con soporte para generación desde planes estratégicos."""

    def get_by_plan_year(self, db: Session, plan_id: int, year: int) -> Optional[POA]:
        return (
            db.query(POA)
            .filter(POA.strategic_plan_id == plan_id, POA.year == year)
            .first()
        )

    def list_by_plan(self, db: Session, plan_id: int) -> List[POA]:
        return db.query(POA).filter(POA.strategic_plan_id == plan_id).all()

    def count_per_year(self, db: Session, year: Optional[int] = None) -> int:
        query = db.query(func.count(POA.id))
        if year:
            query = query.filter(POA.year == year)
        return query.scalar() or 0

    def statistics_by_plan(self, db: Session, plan_id: int) -> Dict[str, int]:
        total = (
            db.query(func.count(POA.id))
            .filter(POA.strategic_plan_id == plan_id)
            .scalar()
            or 0
        )
        budgets = (
            db.query(func.sum(POA.total_budget))
            .filter(POA.strategic_plan_id == plan_id)
            .scalar()
            or 0.0
        )
        return {"total": total, "total_budget": float(budgets)}

    def create_from_plan(
        self,
        db: Session,
        *,
        plan_id: int,
        year: int,
        name: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        total_budget: float = 0.0,
    ) -> POA:
        existing = self.get_by_plan_year(db, plan_id, year)
        if existing:
            raise ValueError("Ya existe un POA para ese año y plan")
        obj = POA(
            strategic_plan_id=plan_id,
            year=year,
            name=name,
            start_date=start_date,
            end_date=end_date,
            total_budget=total_budget,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj


poa_crud = CRUDPOA(POA)
