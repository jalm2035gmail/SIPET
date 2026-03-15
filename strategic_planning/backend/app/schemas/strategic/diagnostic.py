from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import MAINModel, ConfigDict, Field, validator


# ========== SWOT ITEM SCHEMA ==========
class SWOTItem(MAINModel):
    """Item individual para análisis FODA"""
    description: str = Field(..., min_length=5, max_length=500, description="Descripción del factor")
    impact: str = Field("medium", description="Impacto: low, medium, high")
    evidence: Optional[str] = Field(None, max_length=1000, description="Evidencia o datos de soporte")
    suggested_actions: Optional[List[str]] = Field(None, description="Acciones sugeridas")
    category: Optional[str] = Field(None, description="Categoría interna")

    @validator("impact")
    def validate_impact(cls, v):
        if v not in ["low", "medium", "high"]:
            raise ValueError("Impact debe ser low, medium o high")
        return v


# ========== PESTEL ITEM SCHEMA ==========
class PESTELItem(MAINModel):
    """Item individual para análisis PESTEL"""
    factor: str = Field(..., min_length=5, max_length=500, description="Factor identificado")
    trend: str = Field("neutral", description="Tendencia: positive, negative, neutral")
    time_horizon: str = Field("short", description="Horizonte: short, medium, long")
    implications: Optional[str] = Field(None, max_length=1000, description="Implicaciones estratégicas")

    @validator("trend")
    def validate_trend(cls, v):
        if v not in ["positive", "negative", "neutral"]:
            raise ValueError("Trend debe ser positive, negative o neutral")
        return v

    @validator("time_horizon")
    def validate_time_horizon(cls, v):
        if v not in ["short", "medium", "long"]:
            raise ValueError("Time horizon debe ser short, medium o long")
        return v


# ========== CREATE SCHEMA ==========
class DiagnosticAnalysisCreate(MAINModel):
    """Schema para creación de Análisis de Diagnóstico"""
    swot_strengths: Optional[List[SWOTItem]] = Field(None, description="Fortalezas")
    swot_weaknesses: Optional[List[SWOTItem]] = Field(None, description="Debilidades")
    swot_opportunities: Optional[List[SWOTItem]] = Field(None, description="Oportunidades")
    swot_threats: Optional[List[SWOTItem]] = Field(None, description="Amenazas")

    pestel_political: Optional[List[PESTELItem]] = Field(None, description="Factores políticos")
    pestel_economic: Optional[List[PESTELItem]] = Field(None, description="Factores económicos")
    pestel_social: Optional[List[PESTELItem]] = Field(None, description="Factores sociales")
    pestel_technological: Optional[List[PESTELItem]] = Field(None, description="Factores tecnológicos")
    pestel_environmental: Optional[List[PESTELItem]] = Field(None, description="Factores ambientales")
    pestel_legal: Optional[List[PESTELItem]] = Field(None, description="Factores legales")

    porter_supplier_power: Optional[str] = Field(None, description="Poder de proveedores")
    porter_buyer_power: Optional[str] = Field(None, description="Poder de compradores")
    porter_competitive_rivalry: Optional[str] = Field(None, description="Rivalidad competitiva")
    porter_threat_of_substitutes: Optional[str] = Field(None, description="Amenaza de sustitutos")
    porter_threat_of_new_entrants: Optional[str] = Field(None, description="Amenaza de nuevos entrantes")

    customer_perception: Optional[Dict[str, Any]] = Field(None, description="Percepción del cliente")
    market_research: Optional[Dict[str, Any]] = Field(None, description="Investigación de mercado")
    competitor_analysis: Optional[Dict[str, Any]] = Field(None, description="Análisis de competencia")

    key_findings: Optional[str] = Field(None, description="Hallazgos clave")
    strategic_implications: Optional[str] = Field(None, description="Implicaciones estratégicas")
    recommendations: Optional[str] = Field(None, description="Recomendaciones")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "swot_strengths": [
                    {
                        "description": "Equipo altamente capacitado",
                        "impact": "high",
                        "evidence": "Certificaciones y evaluaciones de desempeño",
                    }
                ],
                "key_findings": "Necesidad urgente de transformación digital",
            }
        }
    )


# ========== UPDATE SCHEMA ==========
class DiagnosticAnalysisUpdate(MAINModel):
    """Schema para actualización de Análisis de Diagnóstico"""
    swot_strengths: Optional[List[SWOTItem]] = None
    swot_weaknesses: Optional[List[SWOTItem]] = None
    swot_opportunities: Optional[List[SWOTItem]] = None
    swot_threats: Optional[List[SWOTItem]] = None

    pestel_political: Optional[List[PESTELItem]] = None
    pestel_economic: Optional[List[PESTELItem]] = None
    pestel_social: Optional[List[PESTELItem]] = None
    pestel_technological: Optional[List[PESTELItem]] = None
    pestel_environmental: Optional[List[PESTELItem]] = None
    pestel_legal: Optional[List[PESTELItem]] = None

    porter_supplier_power: Optional[str] = None
    porter_buyer_power: Optional[str] = None
    porter_competitive_rivalry: Optional[str] = None
    porter_threat_of_substitutes: Optional[str] = None
    porter_threat_of_new_entrants: Optional[str] = None

    customer_perception: Optional[Dict[str, Any]] = None
    market_research: Optional[Dict[str, Any]] = None
    competitor_analysis: Optional[Dict[str, Any]] = None

    key_findings: Optional[str] = None
    strategic_implications: Optional[str] = None
    recommendations: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key_findings": "Nuevos hallazgos después de investigación de mercado"
            }
        }
    )


# ========== RESPONSE SCHEMA ==========
class DiagnosticAnalysisResponse(MAINModel):
    """Schema para respuesta de Análisis de Diagnóstico"""
    id: int
    strategic_plan_id: int
    swot_matrix: Dict[str, List[SWOTItem]]
    pestel_categories: Dict[str, List[PESTELItem]]
    porter_forces: Dict[str, Optional[str]]
    customer_perception: Optional[Dict[str, Any]]
    market_research: Optional[Dict[str, Any]]
    competitor_analysis: Optional[Dict[str, Any]]
    key_findings: Optional[str]
    strategic_implications: Optional[str]
    recommendations: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ========== SUMMARY SCHEMA ==========
class DiagnosticSummary(MAINModel):
    """Resumen del diagnóstico"""
    total_swot_items: int
    total_pestel_items: int
    swot_by_impact: Dict[str, int]
    pestel_by_trend: Dict[str, int]
    has_porter_analysis: bool
    has_customer_data: bool
    key_insights: List[str]
