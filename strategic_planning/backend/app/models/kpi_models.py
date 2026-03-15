from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Union, Callable
from enum import Enum
import numpy as np
import pandas as pd
from decimal import Decimal, ROUND_HALF_UP
import json
import hashlib
from abc import ABC, abstractmethod

# ============================================
# ENUMS Y CONSTANTES
# ============================================

class KPIType(Enum):
    """Tipos de KPIs según naturaleza"""
    FINANCIAL = "financial"
    OPERATIONAL = "operational"
    COMMERCIAL = "commercial"
    QUALITY = "quality"
    EFFICIENCY = "efficiency"
    STRATEGIC = "strategic"
    COMPLIANCE = "compliance"
    CUSTOMER = "customer"
    EMPLOYEE = "employee"
    INNOVATION = "innovation"

class KPIFormat(Enum):
    """Formatos de visualización"""
    PERCENTAGE = "%"
    CURRENCY = "$"
    NUMBER = "#"
    DECIMAL = "0.00"
    TIME = "hh:mm"
    DAYS = "days"
    RATIO = "ratio"

class FrequencyType(Enum):
    """Frecuencias de medición"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUAL = "semi_annual"
    ANNUAL = "annual"
    ADHOC = "adhoc"

class CalculationMethod(Enum):
    """Métodos de cálculo"""
    SUM = "sum"
    AVERAGE = "avg"
    COUNT = "count"
    DISTINCT_COUNT = "distinct_count"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    CUSTOM = "custom"
    FORMULA = "formula"

class AlertSeverity(Enum):
    """Niveles de severidad para alertas"""
    INFO = 1
    WARNING = 2
    CRITICAL = 3
    BLOCKER = 4

class AlertStatus(Enum):
    """Estados de alerta"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    IGNORED = "ignored"

class TrendDirection(Enum):
    """Dirección de tendencias"""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"

# ============================================
# MODELO PRINCIPAL DE KPI
# ============================================

@dataclass
class KPI:
    """Modelo completo de KPI con todas las características"""
    
    # Identificación
    id: str
    code: str
    name: str
    description: str
    
    # Clasificación
    type: KPIType
    category: str
    subcategory: Optional[str] = None
    
    # Configuración de medición
    format: KPIFormat = KPIFormat.NUMBER
    frequency: FrequencyType = FrequencyType.MONTHLY
    unit: str = ""
    decimal_places: int = 2
    
    # Fórmula y cálculo
    calculation_method: CalculationMethod = CalculationMethod.SUM
    formula: Optional[str] = None
    data_source: Optional[str] = None
    calculation_dependencies: List[str] = field(default_factory=list)
    
    # Umbrales y objetivos
    target_value: Optional[float] = None
    min_threshold: Optional[float] = None
    max_threshold: Optional[float] = None
    warning_threshold_low: Optional[float] = None
    warning_threshold_high: Optional[float] = None
    critical_threshold_low: Optional[float] = None
    critical_threshold_high: Optional[float] = None
    
    # Polaridad (mayor es mejor, menor es mejor, neutral)
    higher_is_better: bool = True
    benchmark_value: Optional[float] = None
    benchmark_source: Optional[str] = None
    
    # Responsables
    owner: str
    stakeholders: List[str] = field(default_factory=list)
    data_owner: Optional[str] = None
    
    # Metadatos
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    tags: List[str] = field(default_factory=list)
    
    # Configuración avanzada
    seasonality_adjusted: bool = False
    cumulative: bool = False
    yoy_comparison: bool = True
    
    def __post_init__(self):
        """Validaciones post-inicialización"""
        if not self.id:
            self.id = self._generate_id()
        if not self.unit and self.format == KPIFormat.PERCENTAGE:
            self.unit = "%"
    
    def _generate_id(self) -> str:
        """Genera ID único basado en código y timestamp"""
        unique_string = f"{self.code}_{datetime.now().isoformat()}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    def validate_value(self, value: float) -> Dict[str, Any]:
        """Valida un valor contra los umbrales configurados"""
        status = "normal"
        alerts = []
        
        if self.min_threshold is not None and value < self.min_threshold:
            status = "critical"
            alerts.append({
                "type": "min_threshold",
                "severity": AlertSeverity.CRITICAL,
                "message": f"Valor {value} por debajo del mínimo {self.min_threshold}"
            })
        elif self.max_threshold is not None and value > self.max_threshold:
            status = "critical"
            alerts.append({
                "type": "max_threshold",
                "severity": AlertSeverity.CRITICAL,
                "message": f"Valor {value} por encima del máximo {self.max_threshold}"
            })
        elif self.warning_threshold_low is not None and value < self.warning_threshold_low:
            status = "warning"
            alerts.append({
                "type": "warning_low",
                "severity": AlertSeverity.WARNING,
                "message": f"Valor {value} en nivel bajo de advertencia"
            })
        elif self.warning_threshold_high is not None and value > self.warning_threshold_high:
            status = "warning"
            alerts.append({
                "type": "warning_high",
                "severity": AlertSeverity.WARNING,
                "message": f"Valor {value} en nivel alto de advertencia"
            })
        
        return {
            "status": status,
            "alerts": alerts,
            "value": self.format_value(value)
        }
    
    def format_value(self, value: float) -> str:
        """Formatea el valor según el tipo de KPI"""
        if self.format == KPIFormat.PERCENTAGE:
            return f"{value:.{self.decimal_places}f}%"
        elif self.format == KPIFormat.CURRENCY:
            return f"${value:,.{self.decimal_places}f}"
        elif self.format == KPIFormat.DECIMAL:
            return f"{value:.{self.decimal_places}f}"
        elif self.format == KPIFormat.RATIO:
            return f"{value:.{self.decimal_places}}:1"
        else:
            return f"{value:,.0f}"
    
    def calculate_performance(self, actual: float) -> Dict[str, float]:
        """Calcula métricas de rendimiento contra objetivo"""
        if not self.target_value or self.target_value == 0:
            return {"achievement": None, "gap": None, "variance": None}
        
        achievement = (actual / self.target_value) * 100
        gap = actual - self.target_value
        variance = ((actual - self.target_value) / abs(self.target_value)) * 100
        
        return {
            "achievement": achievement,
            "gap": gap,
            "variance": variance
        }

# ============================================
# MODELO DE MEDICIÓN DE KPIs
# ============================================

@dataclass
class KPIMeasurement:
    """Registro de medición de un KPI"""
    
    # Identificación
    id: str
    kpi_id: str
    kpi_code: str
    
    # Valores
    value: float
    formatted_value: str
    previous_value: Optional[float] = None
    
    # Metadatos de medición
    measurement_date: datetime = field(default_factory=datetime.now)
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    frequency: FrequencyType = FrequencyType.DAILY
    
    # Contexto
    source: str
    notes: Optional[str] = None
    measured_by: str
    
    # Validación
    is_validated: bool = False
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    
    # Cálculos derivados
    variance: Optional[float] = None
    variance_percentage: Optional[float] = None
    target_achievement: Optional[float] = None
    
    # Dimensiones
    dimensions: Dict[str, str] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    # Estado
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Calcula valores derivados"""
        if not self.id:
            self.id = self._generate_id()
        
    def _generate_id(self) -> str:
        """Genera ID único para la medición"""
        unique = f"{self.kpi_id}_{self.measurement_date.isoformat()}"
        return hashlib.md5(unique.encode()).hexdigest()[:16]
    
    def calculate_variance(self, MAINline: float) -> None:
        """Calcula varianza contra línea MAIN"""
        self.previous_value = MAINline
        self.variance = self.value - MAINline
        if MAINline != 0:
            self.variance_percentage = (self.variance / abs(MAINline)) * 100
    
    def validate(self, validator: str) -> None:
        """Marca la medición como validada"""
        self.is_validated = True
        self.validated_by = validator
        self.validated_at = datetime.now()
        self.updated_at = datetime.now()

# ============================================
# SISTEMA DE FÓRMULAS Y CÁLCULOS
# ============================================

class KPICalculator(ABC):
    """Clase MAIN abstracta para cálculos de KPIs"""
    
    @abstractmethod
    def calculate(self, data: pd.DataFrame, **kwargs) -> float:
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """Valida que los datos sean adecuados para el cálculo"""
        return not data.empty

class SumCalculator(KPICalculator):
    """Calcula suma de valores"""
    def calculate(self, data: pd.DataFrame, column: str = "value", **kwargs) -> float:
        self.validate_data(data)
        return float(data[column].sum())

class AverageCalculator(KPICalculator):
    """Calcula promedio de valores"""
    def calculate(self, data: pd.DataFrame, column: str = "value", **kwargs) -> float:
        self.validate_data(data)
        return float(data[column].mean())

class CountCalculator(KPICalculator):
    """Cuenta número de registros"""
    def calculate(self, data: pd.DataFrame, **kwargs) -> float:
        self.validate_data(data)
        return float(len(data))

class DistinctCountCalculator(KPICalculator):
    """Cuenta valores distintos"""
    def calculate(self, data: pd.DataFrame, column: str = "value", **kwargs) -> float:
        self.validate_data(data)
        return float(data[column].nunique())

class PercentileCalculator(KPICalculator):
    """Calcula percentil específico"""
    def calculate(self, data: pd.DataFrame, column: str = "value", 
                  percentile: float = 50, **kwargs) -> float:
        self.validate_data(data)
        return float(data[column].quantile(percentile / 100))

class FormulaCalculator(KPICalculator):
    """Calcula usando fórmula personalizada"""
    def __init__(self, formula: str):
        self.formula = formula
        
    def calculate(self, data: pd.DataFrame, **kwargs) -> float:
        self.validate_data(data)
        # Nota: En producción usaría eval con precaución o un parser seguro
        context = {
            'data': data,
            'sum': data['value'].sum(),
            'avg': data['value'].mean(),
            'count': len(data),
            'min': data['value'].min(),
            'max': data['value'].max(),
            **kwargs
        }
        try:
            return float(eval(self.formula, {"__builtins__": {}}, context))
        except Exception as e:
            raise ValueError(f"Error evaluando fórmula: {e}")

class KPICalculationEngine:
    """Motor de cálculo de KPIs"""
    
    def __init__(self):
        self.calculators = {
            CalculationMethod.SUM: SumCalculator(),
            CalculationMethod.AVERAGE: AverageCalculator(),
            CalculationMethod.COUNT: CountCalculator(),
            CalculationMethod.DISTINCT_COUNT: DistinctCountCalculator(),
            CalculationMethod.PERCENTILE: PercentileCalculator(),
        }
    
    def calculate_kpi_value(self, kpi: KPI, measurements: List[KPIMeasurement], 
                           **kwargs) -> Dict[str, Any]:
        """Calcula el valor de un KPI basado en sus mediciones"""
        
        if not measurements:
            return {
                "value": 0,
                "method": kpi.calculation_method,
                "measurements_used": 0,
                "status": "no_data"
            }
        
        # Convertir mediciones a DataFrame
        df = pd.DataFrame([
            {
                "value": m.value,
                "measurement_date": m.measurement_date,
                **m.attributes
            }
            for m in measurements
        ])
        
        # Seleccionar calculadora
        if kpi.calculation_method == CalculationMethod.CUSTOM and kpi.formula:
            calculator = FormulaCalculator(kpi.formula)
        elif kpi.calculation_method == CalculationMethod.FORMULA and kpi.formula:
            calculator = FormulaCalculator(kpi.formula)
        else:
            calculator = self.calculators.get(
                kpi.calculation_method, 
                SumCalculator()
            )
        
        # Calcular valor
        try:
            value = calculator.calculate(df, **kwargs)
            
            # Aplicar redondeo
            if kpi.decimal_places:
                value = float(Decimal(str(value)).quantize(
                    Decimal(f"1.{'0'*kpi.decimal_places}"), 
                    rounding=ROUND_HALF_UP
                ))
            
            return {
                "value": value,
                "method": kpi.calculation_method,
                "measurements_used": len(measurements),
                "calculator_type": calculator.__class__.__name__,
                "status": "success"
            }
        except Exception as e:
            return {
                "value": 0,
                "method": kpi.calculation_method,
                "measurements_used": len(measurements),
                "status": "error",
                "error": str(e)
            }

# ============================================
# GESTOR DE FRECUENCIAS Y AGENDAMIENTO
# ============================================

class FrequencyManager:
    """Gestor de frecuencias de medición"""
    
    def __init__(self):
        self.frequency_configs = {
            FrequencyType.HOURLY: {"days": 1/24, "periods_per_year": 8760},
            FrequencyType.DAILY: {"days": 1, "periods_per_year": 365},
            FrequencyType.WEEKLY: {"days": 7, "periods_per_year": 52},
            FrequencyType.BIWEEKLY: {"days": 14, "periods_per_year": 26},
            FrequencyType.MONTHLY: {"days": 30, "periods_per_year": 12},
            FrequencyType.QUARTERLY: {"days": 91, "periods_per_year": 4},
            FrequencyType.SEMI_ANNUAL: {"days": 182, "periods_per_year": 2},
            FrequencyType.ANNUAL: {"days": 365, "periods_per_year": 1},
        }
    
    def get_next_measurement_date(self, frequency: FrequencyType, 
                                  from_date: datetime = None) -> datetime:
        """Calcula la próxima fecha de medición"""
        if from_date is None:
            from_date = datetime.now()
        
        config = self.frequency_configs.get(frequency)
        if not config:
            return from_date + timedelta(days=30)
        
        return from_date + timedelta(days=config["days"])
    
    def get_period_dates(self, frequency: FrequencyType, 
                        reference_date: datetime = None) -> Dict[str, datetime]:
        """Obtiene fechas de inicio y fin del período actual"""
        if reference_date is None:
            reference_date = datetime.now()
        
        if frequency == FrequencyType.DAILY:
            start = datetime(reference_date.year, reference_date.month, reference_date.day)
            end = start + timedelta(days=1, microseconds=-1)
        elif frequency == FrequencyType.WEEKLY:
            start = reference_date - timedelta(days=reference_date.weekday())
            start = datetime(start.year, start.month, start.day)
            end = start + timedelta(days=7, microseconds=-1)
        elif frequency == FrequencyType.MONTHLY:
            start = datetime(reference_date.year, reference_date.month, 1)
            next_month = start.replace(day=28) + timedelta(days=4)
            end = next_month - timedelta(days=next_month.day)
            end = datetime(end.year, end.month, end.day, 23, 59, 59)
        elif frequency == FrequencyType.QUARTERLY:
            quarter = (reference_date.month - 1) // 3
            start = datetime(reference_date.year, quarter * 3 + 1, 1)
            end_month = (quarter + 1) * 3
            end = datetime(reference_date.year, end_month, 1) + timedelta(days=-1)
            end = datetime(end.year, end.month, end.day, 23, 59, 59)
        else:
            # Default a mensual
            start = datetime(reference_date.year, reference_date.month, 1)
            next_month = start.replace(day=28) + timedelta(days=4)
            end = next_month - timedelta(days=next_month.day)
            end = datetime(end.year, end.month, end.day, 23, 59, 59)
        
        return {"start": start, "end": end}
    
    def is_due_for_measurement(self, kpi: KPI, 
                              last_measurement: Optional[datetime] = None) -> bool:
        """Verifica si un KPI debe ser medido"""
        if not last_measurement:
            return True
        
        next_date = self.get_next_measurement_date(kpi.frequency, last_measurement)
        return datetime.now() >= next_date

# ============================================
# SISTEMA DE ALERTAS Y UMBRALES
# ============================================

@dataclass
class Alert:
    """Modelo de alerta generada por un KPI"""
    
    id: str
    kpi_id: str
    kpi_name: str
    measurement_id: str
    
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    
    title: str
    message: str
    technical_details: Optional[Dict[str, Any]] = None
    
    threshold_type: Optional[str] = None
    threshold_value: Optional[float] = None
    actual_value: Optional[float] = None
    
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    
    assigned_to: Optional[str] = None
    escalation_level: int = 0
    
    def __post_init__(self):
        if not self.id:
            self.id = hashlib.md5(
                f"{self.kpi_id}_{self.measurement_id}_{datetime.now()}".encode()
            ).hexdigest()[:20]
    
    def acknowledge(self, user: str) -> None:
        """Confirma la alerta"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = user
    
    def resolve(self, user: str, resolution_notes: Optional[str] = None) -> None:
        """Resuelve la alerta"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.resolved_by = user
        if resolution_notes:
            if self.technical_details:
                self.technical_details["resolution_notes"] = resolution_notes
            else:
                self.technical_details = {"resolution_notes": resolution_notes}
    
    def escalate(self) -> None:
        """Escala la alerta al siguiente nivel"""
        self.status = AlertStatus.ESCALATED
        self.escalation_level += 1

class AlertingEngine:
    """Motor de generación y gestión de alertas"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_rules = []
        
    def evaluate_kpi_measurement(self, kpi: KPI, measurement: KPIMeasurement) -> List[Alert]:
        """Evalúa una medición y genera alertas si corresponde"""
        alerts = []
        
        # Validar contra umbrales
        validation = kpi.validate_value(measurement.value)
        
        for alert_data in validation["alerts"]:
            severity = alert_data["severity"]
            
            # Solo generar alertas para severidad warning o mayor
            if severity.value >= AlertSeverity.WARNING.value:
                alert = Alert(
                    kpi_id=kpi.id,
                    kpi_name=kpi.name,
                    measurement_id=measurement.id,
                    severity=severity,
                    title=f"Alerta {severity.name}: {kpi.name}",
                    message=alert_data["message"],
                    threshold_type=alert_data["type"],
                    actual_value=measurement.value,
                    threshold_value=(
                        kpi.min_threshold if "min" in alert_data["type"] 
                        else kpi.max_threshold
                    )
                )
                alerts.append(alert)
                self.alerts.append(alert)
        
        return alerts
    
    def evaluate_kpi_trend(self, kpi: KPI, 
                          measurements: List[KPIMeasurement]) -> Optional[Alert]:
        """Evalúa tendencias y genera alertas proactivas"""
        if len(measurements) < 3:
            return None
        
        values = [m.value for m in measurements[-5:]]
        
        # Detectar tendencia peligrosa
        trend = self._detect_trend(values)
        volatility = self._calculate_volatility(values)
        
        if trend == TrendDirection.DOWN and kpi.higher_is_better and volatility > 0.2:
            alert = Alert(
                kpi_id=kpi.id,
                kpi_name=kpi.name,
                measurement_id=measurements[-1].id,
                severity=AlertSeverity.WARNING,
                title=f"Tendencia negativa detectada: {kpi.name}",
                message=f"El KPI muestra tendencia decreciente sostenida con volatilidad {volatility:.1%}",
                technical_details={
                    "trend": trend.value,
                    "volatility": volatility,
                    "last_values": values
                }
            )
            self.alerts.append(alert)
            return alert
        
        return None
    
    def _detect_trend(self, values: List[float]) -> TrendDirection:
        """Detecta la dirección de la tendencia"""
        if len(values) < 2:
            return TrendDirection.UNKNOWN
        
        # Regresión lineal simple
        x = np.arange(len(values))
        y = np.array(values)
        
        if np.std(y) == 0:
            return TrendDirection.STABLE
        
        slope = np.polyfit(x, y, 1)[0]
        
        if slope > 0.01:
            return TrendDirection.UP
        elif slope < -0.01:
            return TrendDirection.DOWN
        else:
            return TrendDirection.STABLE
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calcula volatilidad (coeficiente de variación)"""
        if len(values) < 2:
            return 0
        mean = np.mean(values)
        if mean == 0:
            return 0
        return np.std(values) / abs(mean)
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Obtiene alertas activas"""
        alerts = [a for a in self.alerts if a.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)

# ============================================
# DASHBOARD Y VISUALIZACIÓN DE KPIs
# ============================================

class KPIDashboard:
    """Dashboard de visualización y análisis de KPIs"""
    
    def __init__(self, name: str, organization: str):
        self.name = name
        self.organization = organization
        self.kpis: Dict[str, KPI] = {}
        self.measurements: Dict[str, List[KPIMeasurement]] = {}
        self.alerts: List[Alert] = []
        self.views: Dict[str, Dict] = {}
        
    def add_kpi(self, kpi: KPI) -> None:
        """Agrega un KPI al dashboard"""
        self.kpis[kpi.id] = kpi
        if kpi.id not in self.measurements:
            self.measurements[kpi.id] = []
    
    def add_measurement(self, measurement: KPIMeasurement) -> None:
        """Agrega una medición al dashboard"""
        if measurement.kpi_id in self.kpis:
            self.measurements[measurement.kpi_id].append(measurement)
            # Ordenar por fecha
            self.measurements[measurement.kpi_id].sort(
                key=lambda x: x.measurement_date
            )
    
    def get_kpi_overview(self) -> pd.DataFrame:
        """Genera vista general de todos los KPIs"""
        overview = []
        
        for kpi_id, kpi in self.kpis.items():
            measurements = self.measurements.get(kpi_id, [])
            last_measurement = measurements[-1] if measurements else None
            last_value = last_measurement.value if last_measurement else None
            
            # Calcular tendencia
            trend = self._calculate_trend(kpi_id)
            
            # Última validación
            validated_measurements = [m for m in measurements if m.is_validated]
            last_validated = validated_measurements[-1] if validated_measurements else None
            
            overview.append({
                "kpi_id": kpi_id,
                "kpi_code": kpi.code,
                "kpi_name": kpi.name,
                "type": kpi.type.value,
                "frequency": kpi.frequency.value,
                "owner": kpi.owner,
                "last_value": last_value,
                "formatted_last_value": last_measurement.formatted_value if last_measurement else "N/A",
                "last_measurement_date": last_measurement.measurement_date if last_measurement else None,
                "target": kpi.target_value,
                "achievement": last_measurement.target_achievement if last_measurement else None,
                "trend": trend.value if trend else "unknown",
                "measurements_count": len(measurements),
                "last_validated": last_validated.validated_at if last_validated else None,
                "active": kpi.active,
                "status": self._evaluate_kpi_status(kpi_id)
            })
        
        return pd.DataFrame(overview)
    
    def _calculate_trend(self, kpi_id: str) -> Optional[TrendDirection]:
        """Calcula tendencia para un KPI"""
        measurements = self.measurements.get(kpi_id, [])
        if len(measurements) < 3:
            return None
        
        values = [m.value for m in measurements[-5:]]
        
        if len(values) < 2:
            return TrendDirection.UNKNOWN
        
        slope = np.polyfit(np.arange(len(values)), values, 1)[0]
        
        if slope > 0.01:
            return TrendDirection.UP
        elif slope < -0.01:
            return TrendDirection.DOWN
        else:
            return TrendDirection.STABLE
    
    def _evaluate_kpi_status(self, kpi_id: str) -> str:
        """Evalúa el estado general de un KPI"""
        kpi = self.kpis.get(kpi_id)
        measurements = self.measurements.get(kpi_id, [])
        
        if not measurements:
            return "no_data"
        
        last_value = measurements[-1].value
        validation = kpi.validate_value(last_value)
        
        return validation["status"]
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Genera todos los datos necesarios para el dashboard"""
        overview_df = self.get_kpi_overview()
        
        # KPIs por categoría
        kpis_by_type = overview_df.groupby('type').size().to_dict()
        
        # Estado de KPIs
        status_distribution = overview_df['status'].value_counts().to_dict()
        
        # Últimas mediciones
        recent_measurements = []
        for kpi_id in list(self.kpis.keys())[:10]:
            measurements = self.measurements.get(kpi_id, [])[-3:]
            for m in measurements:
                recent_measurements.append({
                    'kpi_name': self.kpis[kpi_id].name,
                    'value': m.value,
                    'formatted_value': m.formatted_value,
                    'date': m.measurement_date.isoformat(),
                    'validated': m.is_validated
                })
        
        # Alertas activas
        active_alerts = [a for a in self.alerts if a.status in 
                        [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]]
        
        alerts_summary = {
            'critical': len([a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]),
            'warning': len([a for a in active_alerts if a.severity == AlertSeverity.WARNING]),
            'total': len(active_alerts)
        }
        
        return {
            'dashboard_name': self.name,
            'organization': self.organization,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_kpis': len(self.kpis),
                'active_kpis': len([k for k in self.kpis.values() if k.active]),
                'total_measurements': sum(len(m) for m in self.measurements.values()),
                'kpis_by_type': kpis_by_type,
                'status_distribution': status_distribution,
                'alerts_summary': alerts_summary
            },
            'kpi_overview': overview_df.to_dict('records')[:20],
            'recent_measurements': recent_measurements,
            'active_alerts': [
                {
                    'id': a.id,
                    'title': a.title,
                    'severity': a.severity.name,
                    'kpi_name': a.kpi_name,
                    'created_at': a.created_at.isoformat()
                }
                for a in active_alerts[:10]
            ]
        }
    
    def get_kpi_details(self, kpi_id: str) -> Dict[str, Any]:
        """Obtiene detalles completos de un KPI específico"""
        if kpi_id not in self.kpis:
            return {"error": "KPI no encontrado"}
        
        kpi = self.kpis[kpi_id]
        measurements = self.measurements.get(kpi_id, [])
        
        # Series de tiempo
        timeline = [
            {
                'date': m.measurement_date.isoformat(),
                'value': m.value,
                'formatted': m.formatted_value,
                'validated': m.is_validated
            }
            for m in measurements[-30:]
        ]
        
        # Estadísticas
        values = [m.value for m in measurements if m.is_validated]
        stats = {}
        if values:
            stats = {
                'min': min(values),
                'max': max(values),
                'avg': np.mean(values),
                'median': np.median(values),
                'std': np.std(values),
                'count': len(values)
            }
        
        # Rendimiento contra objetivo
        performance = []
        for m in measurements[-12:]:
            perf = kpi.calculate_performance(m.value)
            performance.append({
                'date': m.measurement_date.isoformat(),
                'achievement': perf['achievement'],
                'gap': perf['gap'],
                'variance': perf['variance']
            })
        
        return {
            'kpi': {
                'id': kpi.id,
                'code': kpi.code,
                'name': kpi.name,
                'description': kpi.description,
                'type': kpi.type.value,
                'format': kpi.format.value,
                'unit': kpi.unit,
                'frequency': kpi.frequency.value,
                'owner': kpi.owner,
                'active': kpi.active,
                'created_at': kpi.created_at.isoformat()
            },
            'thresholds': {
                'target': kpi.target_value,
                'min': kpi.min_threshold,
                'max': kpi.max_threshold,
                'warning_low': kpi.warning_threshold_low,
                'warning_high': kpi.warning_threshold_high,
                'critical_low': kpi.critical_threshold_low,
                'critical_high': kpi.critical_threshold_high
            },
            'measurements': {
                'total': len(measurements),
                'validated': len([m for m in measurements if m.is_validated]),
                'last_value': measurements[-1].formatted_value if measurements else None,
                'last_date': measurements[-1].measurement_date.isoformat() if measurements else None,
                'timeline': timeline
            },
            'statistics': stats,
            'performance': performance,
            'alerts': [
                {
                    'id': a.id,
                    'severity': a.severity.name,
                    'message': a.message,
                    'created_at': a.created_at.isoformat(),
                    'status': a.status.value
                }
                for a in self.alerts if a.kpi_id == kpi_id
            ][-10:]
        }

# ============================================
# REPOSITORIO DE DATOS Y SERVICIOS
# ============================================

class KPIRepository:
    """Repositorio para persistencia de KPIs y mediciones"""
    
    def __init__(self):
        # En producción, esto sería una MAIN de datos real
        self.kpis: Dict[str, KPI] = {}
        self.measurements: Dict[str, List[KPIMeasurement]] = {}
        self.alerts: List[Alert] = []
    
    def save_kpi(self, kpi: KPI) -> str:
        """Guarda un KPI"""
        self.kpis[kpi.id] = kpi
        if kpi.id not in self.measurements:
            self.measurements[kpi.id] = []
        return kpi.id
    
    def get_kpi(self, kpi_id: str) -> Optional[KPI]:
        """Obtiene un KPI por ID"""
        return self.kpis.get(kpi_id)
    
    def get_kpi_by_code(self, code: str) -> Optional[KPI]:
        """Obtiene un KPI por código"""
        for kpi in self.kpis.values():
            if kpi.code == code:
                return kpi
        return None
    
    def list_kpis(self, active_only: bool = True) -> List[KPI]:
        """Lista todos los KPIs"""
        if active_only:
            return [k for k in self.kpis.values() if k.active]
        return list(self.kpis.values())
    
    def save_measurement(self, measurement: KPIMeasurement) -> str:
        """Guarda una medición"""
        if measurement.kpi_id in self.measurements:
            self.measurements[measurement.kpi_id].append(measurement)
        else:
            self.measurements[measurement.kpi_id] = [measurement]
        return measurement.id
    
    def get_measurements(self, kpi_id: str, 
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        validated_only: bool = False) -> List[KPIMeasurement]:
        """Obtiene mediciones de un KPI con filtros"""
        measurements = self.measurements.get(kpi_id, [])
        
        if start_date:
            measurements = [m for m in measurements if m.measurement_date >= start_date]
        if end_date:
            measurements = [m for m in measurements if m.measurement_date <= end_date]
        if validated_only:
            measurements = [m for m in measurements if m.is_validated]
        
        return measurements
    
    def save_alert(self, alert: Alert) -> str:
        """Guarda una alerta"""
        self.alerts.append(alert)
        return alert.id
    
    def get_alerts(self, kpi_id: Optional[str] = None,
                  status: Optional[AlertStatus] = None,
                  severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Obtiene alertas con filtros"""
        alerts = self.alerts.copy()
        
        if kpi_id:
            alerts = [a for a in alerts if a.kpi_id == kpi_id]
        if status:
            alerts = [a for a in alerts if a.status == status]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)

class KPIService:
    """Servicio principal para gestión de KPIs"""
    
    def __init__(self):
        self.repository = KPIRepository()
        self.calculation_engine = KPICalculationEngine()
        self.frequency_manager = FrequencyManager()
        self.alerting_engine = AlertingEngine()
        self.dashboards: Dict[str, KPIDashboard] = {}
    
    def create_kpi(self, **kwargs) -> KPI:
        """Crea un nuevo KPI"""
        kpi = KPI(**kwargs)
        self.repository.save_kpi(kpi)
        return kpi
    
    def register_measurement(self, kpi_id: str, value: float, source: str, 
                            measured_by: str, notes: Optional[str] = None,
                            measurement_date: Optional[datetime] = None,
                            period_start: Optional[date] = None,
                            period_end: Optional[date] = None) -> KPIMeasurement:
        """Registra una nueva medición para un KPI"""
        
        kpi = self.repository.get_kpi(kpi_id)
        if not kpi:
            raise ValueError(f"KPI {kpi_id} no encontrado")
        
        # Validar valor
        validation = kpi.validate_value(value)
        
        # Crear medición
        measurement = KPIMeasurement(
            kpi_id=kpi_id,
            kpi_code=kpi.code,
            value=value,
            formatted_value=kpi.format_value(value),
            measurement_date=measurement_date or datetime.now(),
            period_start=period_start,
            period_end=period_end,
            frequency=kpi.frequency,
            source=source,
            notes=notes,
            measured_by=measured_by
        )
        
        # Calcular rendimiento contra objetivo
        if kpi.target_value:
            performance = kpi.calculate_performance(value)
            measurement.target_achievement = performance['achievement']
        
        # Obtener medición anterior para varianza
        previous = self.repository.get_measurements(kpi_id, validated_only=True)
        if previous:
            measurement.calculate_variance(previous[-1].value)
        
        # Guardar medición
        self.repository.save_measurement(measurement)
        
        # Generar alertas
        alerts = self.alerting_engine.evaluate_kpi_measurement(kpi, measurement)
        for alert in alerts:
            self.repository.save_alert(alert)
        
        # Evaluar tendencia
        all_measurements = self.repository.get_measurements(kpi_id)
        trend_alert = self.alerting_engine.evaluate_kpi_trend(kpi, all_measurements)
        if trend_alert:
            self.repository.save_alert(trend_alert)
        
        # Actualizar dashboards
        for dashboard in self.dashboards.values():
            if kpi_id in dashboard.kpis:
                dashboard.add_measurement(measurement)
                dashboard.alerts.extend(alerts)
                if trend_alert:
                    dashboard.alerts.append(trend_alert)
        
        return measurement
    
    def validate_measurement(self, measurement_id: str, kpi_id: str, 
                            validator: str) -> KPIMeasurement:
        """Valida una medición"""
        measurements = self.repository.get_measurements(kpi_id)
        
        measurement = next(
            (m for m in measurements if m.id == measurement_id), 
            None
        )
        
        if not measurement:
            raise ValueError(f"Medición {measurement_id} no encontrada")
        
        measurement.validate(validator)
        return measurement
    
    def calculate_kpi_value(self, kpi_id: str, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Calcula el valor actual de un KPI basado en mediciones recientes"""
        
        kpi = self.repository.get_kpi(kpi_id)
        if not kpi:
            raise ValueError(f"KPI {kpi_id} no encontrado")
        
        # Obtener período actual
        if not start_date or not end_date:
            period = self.frequency_manager.get_period_dates(kpi.frequency)
            start_date = period['start']
            end_date = period['end']
        
        # Obtener mediciones del período
        measurements = self.repository.get_measurements(
            kpi_id, 
            start_date=start_date,
            end_date=end_date,
            validated_only=True
        )
        
        # Calcular
        result = self.calculation_engine.calculate_kpi_value(kpi, measurements)
        
        return {
            **result,
            'kpi_id': kpi_id,
            'kpi_name': kpi.name,
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
            'formatted_value': kpi.format_value(result['value']) if result['status'] == 'success' else "N/A"
        }
    
    def create_dashboard(self, name: str, organization: str) -> KPIDashboard:
        """Crea un nuevo dashboard"""
        dashboard = KPIDashboard(name, organization)
        self.dashboards[name] = dashboard
        return dashboard
    
    def add_kpi_to_dashboard(self, dashboard_name: str, kpi_id: str) -> None:
        """Agrega un KPI a un dashboard"""
        if dashboard_name not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_name} no encontrado")
        
        kpi = self.repository.get_kpi(kpi_id)
        if not kpi:
            raise ValueError(f"KPI {kpi_id} no encontrado")
        
        dashboard = self.dashboards[dashboard_name]
        dashboard.add_kpi(kpi)
        
        # Cargar mediciones existentes
        measurements = self.repository.get_measurements(kpi_id)
        for measurement in measurements:
            dashboard.add_measurement(measurement)
        
        # Cargar alertas existentes
        alerts = self.repository.get_alerts(kpi_id=kpi_id, 
                                           status=AlertStatus.ACTIVE)
        dashboard.alerts.extend(alerts)
    
    def get_dashboard_data(self, dashboard_name: str) -> Dict[str, Any]:
        """Obtiene datos de un dashboard"""
        if dashboard_name not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_name} no encontrado")
        
        return self.dashboards[dashboard_name].generate_dashboard_data()

# ============================================
# EJEMPLO DE USO Y PRUEBAS
# ============================================

def ejemplo_completo_kpis():
    """Ejemplo completo de uso del sistema de KPIs"""
    
    print("=" * 80)
    print("SISTEMA DE KPIS - EJEMPLO DE IMPLEMENTACIÓN")
    print("=" * 80)
    
    # Inicializar servicio
    service = KPIService()
    
    print("\n1. CREANDO KPIs...")
    print("-" * 40)
    
    # Crear KPI 1: Ingresos mensuales
    kpi_ingresos = service.create_kpi(
        code="REV-001",
        name="Ingresos Mensuales",
        description="Ingresos totales del mes",
        type=KPIType.FINANCIAL,
        category="Ingresos",
        format=KPIFormat.CURRENCY,
        frequency=FrequencyType.MONTHLY,
        unit="USD",
        decimal_places=0,
        calculation_method=CalculationMethod.SUM,
        target_value=1000000,
        min_threshold=800000,
        max_threshold=1200000,
        warning_threshold_low=850000,
        warning_threshold_high=1150000,
        critical_threshold_low=800000,
        critical_threshold_high=1200000,
        higher_is_better=True,
        owner="Finanzas",
        tags=["ingresos", "ventas", "mensual"]
    )
    print(f"✓ KPI creado: {kpi_ingresos.code} - {kpi_ingresos.name}")
    
    # Crear KPI 2: Satisfacción cliente
    kpi_csat = service.create_kpi(
        code="CSAT-001",
        name="Satisfacción del Cliente",
        description="NPS / CSAT Score",
        type=KPIType.CUSTOMER,
        category="Experiencia",
        format=KPIFormat.PERCENTAGE,
        frequency=FrequencyType.WEEKLY,
        unit="%",
        decimal_places=1,
        calculation_method=CalculationMethod.AVERAGE,
        target_value=85,
        min_threshold=70,
        warning_threshold_low=75,
        critical_threshold_low=70,
        higher_is_better=True,
        owner="Customer Experience",
        tags=["satisfacción", "nps", "cliente"]
    )
    print(f"✓ KPI creado: {kpi_csat.code} - {kpi_csat.name}")
    
    # Crear KPI 3: Eficiencia operacional
    kpi_eficiencia = service.create_kpi(
        code="OEE-001",
        name="Eficiencia Operacional",
        description="OEE - Overall Equipment Effectiveness",
        type=KPIType.EFFICIENCY,
        category="Producción",
        format=KPIFormat.PERCENTAGE,
        frequency=FrequencyType.DAILY,
        unit="%",
        decimal_places=1,
        calculation_method=CalculationMethod.FORMULA,
        formula="data['value'].mean() * 0.8 + 20",
        target_value=85,
        min_threshold=70,
        warning_threshold_low=75,
        critical_threshold_low=70,
        higher_is_better=True,
        owner="Operaciones",
        tags=["eficiencia", "producción", "oee"]
    )
    print(f"✓ KPI creado: {kpi_eficiencia.code} - {kpi_eficiencia.name}")
    
    print("\n2. REGISTRANDO MEDICIONES...")
    print("-" * 40)
    
    # Mediciones para ingresos
    mediciones_ingresos = [
        (950000, "Sistema Contable", "admin"),
        (1020000, "Sistema Contable", "admin"),
        (880000, "Sistema Contable", "admin"),
        (980000, "Sistema Contable", "admin"),
        (1050000, "Sistema Contable", "admin"),
    ]
    
    for valor, fuente, medidor in mediciones_ingresos:
        medicion = service.register_measurement(
            kpi_id=kpi_ingresos.id,
            value=valor,
            source=fuente,
            measured_by=medidor
        )
        print(f"  → Registrado: {kpi_ingresos.code} = {medicion.formatted_value}")
    
    # Mediciones para satisfacción
    mediciones_csat = [
        (82.5, "Encuesta NPS", "analista"),
        (84.0, "Encuesta NPS", "analista"),
        (79.5, "Encuesta NPS", "analista"),
        (81.0, "Encuesta NPS", "analista"),
        (76.5, "Encuesta NPS", "analista"),
    ]
    
    for valor, fuente, medidor in mediciones_csat:
        medicion = service.register_measurement(
            kpi_id=kpi_csat.id,
            value=valor,
            source=fuente,
            measured_by=medidor
        )
        print(f"  → Registrado: {kpi_csat.code} = {medicion.formatted_value}")
    
    # Mediciones para eficiencia
    mediciones_oee = [
        (78.3, "Sistema MES", "supervisor"),
        (79.1, "Sistema MES", "supervisor"),
        (76.8, "Sistema MES", "supervisor"),
        (77.5, "Sistema MES", "supervisor"),
        (75.2, "Sistema MES", "supervisor"),
    ]
    
    for valor, fuente, medidor in mediciones_oee:
        medicion = service.register_measurement(
            kpi_id=kpi_eficiencia.id,
            value=valor,
            source=fuente,
            measured_by=medidor
        )
        print(f"  → Registrado: {kpi_eficiencia.code} = {medicion.formatted_value}")
    
    print("\n3. VALIDANDO MEDICIONES...")
    print("-" * 40)
    
    measurements = service.repository.get_measurements(kpi_ingresos.id)
    for m in measurements[-2:]:
        service.validate_measurement(m.id, kpi_ingresos.id, "validador_finanzas")
        print(f"  ✓ Validada: {kpi_ingresos.code} - {m.formatted_value}")
    
    print("\n4. CALCULANDO VALORES AGREGADOS...")
    print("-" * 40)
    
    resultado = service.calculate_kpi_value(kpi_ingresos.id)
    print(f"  KPI {kpi_ingresos.code}:")
    print(f"    - Valor calculado: {resultado['formatted_value']}")
    print(f"    - Método: {resultado['method'].value}")
    print(f"    - Mediciones usadas: {resultado['measurements_used']}")
    print(f"    - Período: {resultado['period_start']} a {resultado['period_end']}")
    
    print("\n5. CREANDO DASHBOARD...")
    print("-" * 40)
    
    dashboard = service.create_dashboard("Dashboard Estratégico", "Mi Empresa S.A.")
    service.add_kpi_to_dashboard("Dashboard Estratégico", kpi_ingresos.id)
    service.add_kpi_to_dashboard("Dashboard Estratégico", kpi_csat.id)
    service.add_kpi_to_dashboard("Dashboard Estratégico", kpi_eficiencia.id)
    print("✓ Dashboard creado y KPIs agregados")
    
    print("\n6. GENERANDO DATOS DE DASHBOARD...")
    print("-" * 40)
    
    dashboard_data = service.get_dashboard_data("Dashboard Estratégico")
    
    print(f"  Resumen:")
    print(f"    - Total KPIs: {dashboard_data['summary']['total_kpis']}")
    print(f"    - Total Mediciones: {dashboard_data['summary']['total_measurements']}")
    print(f"    - Alertas Críticas: {dashboard_data['summary']['alerts_summary']['critical']}")
    print(f"    - Alertas Advertencia: {dashboard_data['summary']['alerts_summary']['warning']}")
    
    print("\n  KPIs en dashboard:")
    for kpi in dashboard_data['kpi_overview']:
        status_icon = "✅" if kpi['status'] == 'normal' else "⚠️" if kpi['status'] == 'warning' else "🔴"
        print(f"    {status_icon} {kpi['kpi_code']}: {kpi['kpi_name']}")
        print(f"       Último valor: {kpi['formatted_last_value']} | "
              f"Objetivo: {kpi['target']} | "
              f"Logro: {kpi['achievement']:.1f}%" if kpi['achievement'] else "")
    
    print("\n7. ALERTAS GENERADAS...")
    print("-" * 40)
    
    alerts = service.repository.get_alerts(status=AlertStatus.ACTIVE)
    for alert in alerts[:3]:
        severity_icon = "🔴" if alert.severity == AlertSeverity.CRITICAL else "🟡"
        print(f"  {severity_icon} [{alert.severity.name}] {alert.title}")
        print(f"     {alert.message}")
        print(f"     Creada: {alert.created_at.strftime('%Y-%m-%d %H:%M')}")
        print()
    
    print("\n8. DETALLE DE KPI ESPECÍFICO...")
    print("-" * 40)
    
    detalle = dashboard.get_kpi_details(kpi_csat.id)
    print(f"  KPI: {detalle['kpi']['name']} ({detalle['kpi']['code']})")
    print(f"  Descripción: {detalle['kpi']['description']}")
    print(f"  Propietario: {detalle['kpi']['owner']}")
    print(f"  Frecuencia: {detalle['kpi']['frequency']}")
    print(f"  Mediciones totales: {detalle['measurements']['total']}")
    print(f"  Mediciones validadas: {detalle['measurements']['validated']}")
    
    if detalle['statistics']:
        print(f"  Estadísticas:")
        print(f"    - Promedio: {kpi_csat.format_value(detalle['statistics']['avg'])}")
        print(f"    - Mínimo: {kpi_csat.format_value(detalle['statistics']['min'])}")
        print(f"    - Máximo: {kpi_csat.format_value(detalle['statistics']['max'])}")
    
    print("\n" + "=" * 80)
    print("✅ SISTEMA DE KPIS IMPLEMENTADO CORRECTAMENTE")
    print("=" * 80)
    
    return service, dashboard

# ============================================
# PUNTO DE ENTRADA
# ============================================

if __name__ == "__main__":
    # Ejecutar ejemplo completo
    service, dashboard = ejemplo_completo_kpis()
    
    # Demostración adicional: Análisis de tendencias
    print("\n" + "=" * 80)
    print("ANÁLISIS DE TENDENCIAS")
    print("=" * 80)
    
    # Obtener tendencias de los KPIs
    overview = dashboard.get_kpi_overview()
    
    for _, row in overview.iterrows():
        trend_icon = "📈" if row['trend'] == 'up' else "📉" if row['trend'] == 'down' else "➡️"
        print(f"{trend_icon} {row['kpi_code']}: Tendencia {row['trend'].upper()}")
    
    print("\n" + "=" * 80)
    print("FIN DEL EJEMPLO")
    print("=" * 80)
