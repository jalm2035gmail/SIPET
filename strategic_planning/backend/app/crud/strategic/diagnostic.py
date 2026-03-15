from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.crud.MAIN import CRUDMAIN
from app.models.strategic.diagnostic import DiagnosticAnalysis
from app.schemas.strategic.diagnostic import DiagnosticAnalysisCreate, DiagnosticAnalysisUpdate


class CRUDDiagnosticAnalysis(CRUDMAIN[DiagnosticAnalysis, DiagnosticAnalysisCreate, DiagnosticAnalysisUpdate]):
    """Operaciones CRUD para DiagnosticAnalysis."""

    def get_by_plan_id(self, db: Session, plan_id: int) -> Optional[DiagnosticAnalysis]:
        """Obtiene un diagnóstico a partir del plan estratégico."""
        return (
            db.query(DiagnosticAnalysis)
            .filter(DiagnosticAnalysis.strategic_plan_id == plan_id)
            .first()
        )

    def create_for_plan(
        self,
        db: Session,
        *,
        plan_id: int,
        obj_in: DiagnosticAnalysisCreate,
        user_id: int,
    ) -> DiagnosticAnalysis:
        """Crea un diagnóstico y evita duplicados por plan."""
        existing = self.get_by_plan_id(db, plan_id)
        if existing:
            raise ValueError("El plan ya tiene un análisis de diagnóstico")

        db_obj = DiagnosticAnalysis(
            strategic_plan_id=plan_id,
            **obj_in.model_dump(),
            created_by=user_id,
            updated_by=user_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_for_plan(
        self,
        db: Session,
        *,
        plan_id: int,
        obj_in: DiagnosticAnalysisUpdate,
        user_id: int,
    ) -> Optional[DiagnosticAnalysis]:
        """Actualiza el diagnóstico vinculado a un plan específico."""
        db_obj = self.get_by_plan_id(db, plan_id)
        if not db_obj:
            return None

        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["updated_by"] = user_id

        return super().update(db, db_obj=db_obj, obj_in=update_data)

    def get_swot_matrix(self, db: Session, plan_id: int) -> Dict[str, Any]:
        """Retorna la matriz FODA ya estructurada."""
        db_obj = self.get_by_plan_id(db, plan_id)
        if not db_obj:
            return {}

        return db_obj.get_swot_matrix()

    def get_summary(self, db: Session, plan_id: int) -> Dict[str, Any]:
        """Resumen estadístico del diagnóstico."""
        db_obj = self.get_by_plan_id(db, plan_id)
        if not db_obj:
            return {"has_diagnostic": False}

        swot_matrix = db_obj.get_swot_matrix()
        pestel_categories = db_obj.get_pestel_categories()

        total_swot = sum(len(items) for items in swot_matrix.values())
        total_pestel = sum(len(items) for items in pestel_categories.values())

        swot_by_impact = {"high": 0, "medium": 0, "low": 0}
        for items in swot_matrix.values():
            for item in items:
                if isinstance(item, dict) and "impact" in item:
                    swot_by_impact[item["impact"]] += 1

        pestel_by_trend = {"positive": 0, "negative": 0, "neutral": 0}
        for items in pestel_categories.values():
            for item in items:
                if isinstance(item, dict) and "trend" in item:
                    pestel_by_trend[item["trend"]] += 1

        return {
            "has_diagnostic": True,
            "total_swot_items": total_swot,
            "total_pestel_items": total_pestel,
            "swot_by_impact": swot_by_impact,
            "pestel_by_trend": pestel_by_trend,
            "has_porter_analysis": bool(db_obj.porter_supplier_power),
            "has_customer_data": bool(db_obj.customer_perception),
            "key_insights": [
                insight
                for insight in [db_obj.key_findings, db_obj.strategic_implications]
                if insight
            ],
        }


diagnostic_analysis = CRUDDiagnosticAnalysis(DiagnosticAnalysis)
