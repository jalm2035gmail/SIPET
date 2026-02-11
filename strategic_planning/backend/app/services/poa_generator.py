from app.models.strategic import StrategicPlan
from app.models.operational import POA

class POAGenerator:
    def generate_from_strategic_plan(self, strategic_plan: StrategicPlan, year: int):
        """Convierte objetivos estratégicos en actividades operativas"""
        poa = POA(year=year, strategic_plan_id=strategic_plan.id)
        
        for axis in strategic_plan.strategic_axes:
            for objective in axis.objectives:
                # Desglosar objetivo en actividades por departamento
                activities = self._break_down_objective(objective, year)
                poa.activities.extend(activities)
        
        return poa

    def _break_down_objective(self, objective, year):
        # Lógica para desglosar objetivo en actividades
        # Retorna lista de actividades
        return []
