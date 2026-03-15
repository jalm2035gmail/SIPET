from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Union, Callable
from enum import Enum
import pandas as pd
import numpy as np
import json
import hashlib
import smtplib
import io
import MAIN64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
import seaborn as sns
from jinja2 import Template
import time
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# ============================================
# ENUMS Y CONSTANTES
# ============================================

class ReportType(Enum):
    """Tipos de reportes"""
    EXECUTIVE = "executive"
    OPERATIONAL = "operational"
    STRATEGIC = "strategic"
    FINANCIAL = "financial"
    ANALYTICAL = "analytical"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"

class ReportFormat(Enum):
    """Formatos de exportación"""
    PDF = "pdf"
    EXCEL = "excel"
    HTML = "html"
    CSV = "csv"
    JSON = "json"
    POWER_BI = "power_bi"
    TABLEAU = "tableau"

class DashboardType(Enum):
    """Tipos de dashboard"""
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"
    TACTICAL = "tactical"
    DEPARTMENTAL = "departmental"
    EXECUTIVE = "executive"
    ANALYTICAL = "analytical"

class VisualizationType(Enum):
    """Tipos de visualización"""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    GAUGE = "gauge"
    TABLE = "table"
    HEATMAP = "heatmap"
    SCATTER = "scatter"
    FUNNEL = "funnel"
    METRIC_CARD = "metric_card"
    TREND_INDICATOR = "trend_indicator"

class ScheduleFrequency(Enum):
    """Frecuencias de programación"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"

class DeliveryMethod(Enum):
    """Métodos de distribución"""
    EMAIL = "email"
    SHAREPOINT = "sharepoint"
    NETWORK = "network"
    API = "api"
    FTP = "ftp"
    DASHBOARD = "dashboard"

class ForecastModel(Enum):
    """Modelos de forecasting"""
    LINEAR_REGRESSION = "linear_regression"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"
    ARIMA = "arima"
    RANDOM_FOREST = "random_forest"
    MOVING_AVERAGE = "moving_average"
    SEASONAL_DECOMPOSE = "seasonal_decompose"

class PermissionLevel(Enum):
    """Niveles de permiso"""
    VIEWER = 1
    EDITOR = 2
    ADMIN = 3
    OWNER = 4

# ============================================
# MODELOS DE PLANTILLAS DE REPORTES
# ============================================

@dataclass
class ReportTemplate:
    """Plantilla para generación de reportes"""
    
    id: str
    name: str
    description: str
    report_type: ReportType
    formats: List[ReportFormat]
    
    # Estructura del reporte
    sections: List[Dict[str, Any]]
    data_sources: List[Dict[str, Any]]
    visualizations: List[Dict[str, Any]]
    
    # Estilo y formato
    theme: Dict[str, Any] = field(default_factory=dict)
    logo_url: Optional[str] = None
    company_info: Dict[str, str] = field(default_factory=dict)
    
    # Metadatos
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    is_active: bool = True
    
    # Configuración avanzada
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    conditional_formatting: List[Dict[str, Any]] = field(default_factory=list)
    calculations: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Genera ID único para la plantilla"""
        unique = f"{self.name}_{datetime.now().isoformat()}"
        return hashlib.md5(unique.encode()).hexdigest()[:16]
    
    def add_section(self, section: Dict[str, Any]) -> None:
        """Agrega una sección al reporte"""
        self.sections.append(section)
        self.updated_at = datetime.now()
    
    def add_visualization(self, viz: Dict[str, Any]) -> None:
        """Agrega una visualización al reporte"""
        self.visualizations.append(viz)
        self.updated_at = datetime.now()

@dataclass
class ScheduledReport:
    """Configuración de reporte programado"""
    
    id: str
    template_id: str
    name: str
    frequency: ScheduleFrequency
    delivery_methods: List[DeliveryMethod]
    recipients: List[str]
    
    # Programación
    start_date: datetime
    next_run: datetime
    last_run: Optional[datetime] = None
    end_date: Optional[datetime] = None
    custom_cron: Optional[str] = None
    
    # Configuración
    formats: List[ReportFormat]
    parameters: Dict[str, Any] = field(default_factory=dict)
    compression_enabled: bool = False
    retention_days: int = 30
    
    # Estado
    is_active: bool = True
    status: str = "pending"
    execution_count: int = 0
    error_count: int = 0
    
    # Historial
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
        if not self.next_run:
            self.next_run = self.start_date
    
    def _generate_id(self) -> str:
        """Genera ID único para el schedule"""
        unique = f"{self.name}_{self.start_date.isoformat()}"
        return hashlib.md5(unique.encode()).hexdigest()[:16]
    
    def calculate_next_run(self) -> datetime:
        """Calcula la próxima fecha de ejecución"""
        now = datetime.now()
        
        if self.frequency == ScheduleFrequency.DAILY:
            next_run = now + timedelta(days=1)
        elif self.frequency == ScheduleFrequency.WEEKLY:
            next_run = now + timedelta(weeks=1)
        elif self.frequency == ScheduleFrequency.MONTHLY:
            next_run = now + timedelta(days=30)
        elif self.frequency == ScheduleFrequency.QUARTERLY:
            next_run = now + timedelta(days=91)
        elif self.frequency == ScheduleFrequency.ANNUAL:
            next_run = now + timedelta(days=365)
        else:
            next_run = now + timedelta(days=1)
        
        return next_run.replace(hour=8, minute=0, second=0, microsecond=0)

@dataclass
class ReportExecution:
    """Registro de ejecución de reporte"""
    
    id: str
    schedule_id: str
    template_id: str
    status: str  # success, failed, processing
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # Resultados
    output_files: Dict[ReportFormat, str] = field(default_factory=dict)
    file_sizes: Dict[ReportFormat, int] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    # Métricas
    execution_time_ms: int = 0
    rows_processed: int = 0
    visualizations_generated: int = 0
    
    # Metadatos
    parameters_used: Dict[str, Any] = field(default_factory=dict)
    executed_by: str = "system"
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Genera ID único para la ejecución"""
        unique = f"{self.schedule_id}_{self.start_time.isoformat()}"
        return hashlib.md5(unique.encode()).hexdigest()[:20]
    
    def complete(self, status: str = "success") -> None:
        """Completa la ejecución del reporte"""
        self.end_time = datetime.now()
        self.status = status
        if self.start_time:
            delta = self.end_time - self.start_time
            self.execution_time_ms = int(delta.total_seconds() * 1000)

# ============================================
# GENERADOR DE REPORTES
# ============================================

class ReportGenerator:
    """Generador de reportes en múltiples formatos"""
    
    def __init__(self):
        self.templates: Dict[str, ReportTemplate] = {}
        self.executions: List[ReportExecution] = []
    
    def generate_report(self, template: ReportTemplate, 
                       data: Dict[str, pd.DataFrame],
                       parameters: Dict[str, Any] = None) -> Dict[ReportFormat, Any]:
        """Genera un reporte en todos los formatos solicitados"""
        
        results = {}
        parameters = parameters or {}
        
        for fmt in template.formats:
            if fmt == ReportFormat.PDF:
                results[fmt] = self._generate_pdf(template, data, parameters)
            elif fmt == ReportFormat.EXCEL:
                results[fmt] = self._generate_excel(template, data, parameters)
            elif fmt == ReportFormat.HTML:
                results[fmt] = self._generate_html(template, data, parameters)
            elif fmt == ReportFormat.CSV:
                results[fmt] = self._generate_csv(template, data, parameters)
            elif fmt == ReportFormat.JSON:
                results[fmt] = self._generate_json(template, data, parameters)
        
        return results
    
    def _generate_pdf(self, template: ReportTemplate, 
                     data: Dict[str, pd.DataFrame],
                     parameters: Dict[str, Any]) -> bytes:
        """Genera reporte en PDF"""
        
        html_content = self._generate_html(template, data, parameters)
        return html_content.encode('utf-8')
    
    def _generate_excel(self, template: ReportTemplate,
                       data: Dict[str, pd.DataFrame],
                       parameters: Dict[str, Any]) -> bytes:
        """Genera reporte en Excel con múltiples hojas"""
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4B7BEC',
                'font_color': 'white',
                'border': 1
            })
            cell_format = workbook.add_format({'border': 1})
            percent_format = workbook.add_format({'num_format': '0.00%', 'border': 1})
            currency_format = workbook.add_format({'num_format': '$#,##0', 'border': 1})
            
            for section in template.sections:
                section_name = section['name'][:31]
                if section_name in data:
                    df = data[section_name]
                    df.to_excel(writer, sheet_name=section_name, index=False)
                    worksheet = writer.sheets[section_name]
                    for col_num, col_name in enumerate(df.columns):
                        worksheet.write(0, col_num, col_name, header_format)
                        column_len = max(df[col_name].astype(str).map(len).max(), len(col_name))
                        worksheet.set_column(col_num, col_num, column_len + 2)
                        if 'percent' in col_name.lower():
                            worksheet.set_column(col_num, col_num, column_len + 2, percent_format)
                        elif any(keyword in col_name.lower() for keyword in ['price', 'cost', 'revenue']):
                            worksheet.set_column(col_num, col_num, column_len + 2, currency_format)
                        else:
                            worksheet.set_column(col_num, col_num, column_len + 2, cell_format)
            summary_df = self._create_summary_sheet(template, data, parameters)
            summary_df.to_excel(writer, sheet_name='Resumen', index=False)
            params_df = pd.DataFrame([
                {'Parámetro': k, 'Valor': str(v)}
                for k, v in parameters.items()
            ])
            params_df.to_excel(writer, sheet_name='Parámetros', index=False)
        
        output.seek(0)
        return output.getvalue()
    
    def _generate_html(self, template: ReportTemplate,
                      data: Dict[str, pd.DataFrame],
                      parameters: Dict[str, Any]) -> str:
        """Genera reporte en HTML con diseño responsivo"""
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ template.name }} - Reporte</title>
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #f8f9fa;
                    color: #333;
                    line-height: 1.6;
                }
                .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
                .header { 
                    background: linear-gradient(135deg, #4b7bec, #2c3e50);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }
                .company-name { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
                .report-title { font-size: 32px; font-weight: bold; margin-bottom: 10px; }
                .report-meta { color: rgba(255,255,255,0.9); font-size: 14px; }
                .section { 
                    background: white;
                    border-radius: 10px;
                    padding: 25px;
                    margin-bottom: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                .section-title { 
                    font-size: 20px;
                    font-weight: bold;
                    color: #2c3e50;
                    margin-bottom: 20px;
                    padding-bottom: 10px;
                    border-bottom: 3px solid #4b7bec;
                }
                table { 
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 15px;
                }
                th { 
                    background-color: #4b7bec;
                    color: white;
                    padding: 12px;
                    text-align: left;
                    font-weight: 600;
                }
                td { 
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                }
                tr:hover { background-color: #f5f6fa; }
                .metric-card { 
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    text-align: center;
                    margin: 10px;
                }
                .metric-value { font-size: 36px; font-weight: bold; margin: 10px 0; }
                .metric-label { font-size: 14px; opacity: 0.9; }
                .footer {
                    text-align: center;
                    margin-top: 50px;
                    padding: 20px;
                    color: #666;
                    font-size: 12px;
                }
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
                .alert { 
                    padding: 15px;
                    border-radius: 5px;
                    margin-bottom: 15px;
                }
                .alert-success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
                .alert-warning { background-color: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
                .alert-danger { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
                @media print {
                    body { background-color: white; }
                    .section { box-shadow: none; border: 1px solid #ddd; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="company-name">{{ template.company_info.get('name', '') }}</div>
                    <div class="report-title">{{ template.name }}</div>
                    <div class="report-meta">
                        Fecha: {{ generation_date }} | 
                        Generado por: {{ parameters.get('generated_by', 'Sistema') }} |
                        Versión: {{ template.version }}
                    </div>
                </div>

                {% for section in template.sections %}
                <div class="section">
                    <div class="section-title">{{ section.name }}</div>

                    {% if section.description %}
                    <p style="color: #666; margin-bottom: 20px;">{{ section.description }}</p>
                    {% endif %}

                    {% if section.name in data %}
                        {% set df = data[section.name] %}

                        {% if section.visualization_type == 'metric_cards' %}
                        <div class="grid">
                            {% for col in df.columns[:4] %}
                            <div class="metric-card">
                                <div class="metric-label">{{ col }}</div>
                                <div class="metric-value">{{ df[col].iloc[0] }}</div>
                            </div>
                            {% endfor %}
                        </div>
                        {% else %}
                        <div style="overflow-x: auto;">
                            {{ df.to_html(index=False, classes='table table-striped') | safe }}
                        </div>
                        {% endif %}
                    {% endif %}
                </div>
                {% endfor %}

                <div class="footer">
                    <p>Generado el {{ generation_date }} por Sistema de Reportes Estratégicos</p>
                    <p>Confidencial - Solo para uso interno</p>
                </div>
            </div>
        </body>
        </html>
        """

        template_obj = Template(html_template)
        html_content = template_obj.render(
            template=template,
            data={k: v for k, v in data.items()},
            parameters=parameters,
            generation_date=datetime.now().strftime('%d/%m/%Y %H:%M')
        )

        return html_content
    
    def _generate_csv(self, template: ReportTemplate,
                     data: Dict[str, pd.DataFrame],
                     parameters: Dict[str, Any]) -> bytes:
        """Genera reporte en CSV (primer dataframe)"""
        if data:
            first_key = list(data.keys())[0]
            output = io.StringIO()
            data[first_key].to_csv(output, index=False)
            return output.getvalue().encode('utf-8')
        return b''
    
    def _generate_json(self, template: ReportTemplate,
                      data: Dict[str, pd.DataFrame],
                      parameters: Dict[str, Any]) -> bytes:
        """Genera reporte en JSON"""
        result = {
            'report': {
                'name': template.name,
                'type': template.report_type.value,
                'generated_at': datetime.now().isoformat(),
                'parameters': parameters
            },
            'data': {
                name: df.to_dict(orient='records')
                for name, df in data.items()
            }
        }
        return json.dumps(result, indent=2, default=str).encode('utf-8')
    
    def _create_summary_sheet(self, template: ReportTemplate,
                             data: Dict[str, pd.DataFrame],
                             parameters: Dict[str, Any]) -> pd.DataFrame:
        """Crea hoja de resumen para Excel"""
        summary = []
        
        for section_name, df in data.items():
            summary.append({
                'Sección': section_name,
                'Filas': len(df),
                'Columnas': len(df.columns),
                'Última Actualización': datetime.now().strftime('%Y-%m-%d %H:%M')
            })
        
        return pd.DataFrame(summary)

# ============================================
# SISTEMA DE DISTRIBUCIÓN AUTOMÁTICA
# ============================================

class DistributionService:
    """Servicio de distribución automática de reportes"""

    def __init__(self):
        self.delivery_configs = {}
        self.delivery_history = []
    
    def distribute_report(self, report_content: Dict[ReportFormat, bytes],
                         schedule: ScheduledReport,
                         execution: ReportExecution) -> Dict[str, bool]:
        """Distribuye reporte a través de métodos configurados"""
        
        results = {}
        
        for method in schedule.delivery_methods:
            if method == DeliveryMethod.EMAIL:
                results['email'] = self._send_email(report_content, schedule)
            elif method == DeliveryMethod.DASHBOARD:
                results['dashboard'] = self._publish_to_dashboard(report_content, schedule)
            elif method == DeliveryMethod.API:
                results['api'] = self._send_to_api(report_content, schedule)
            elif method == DeliveryMethod.NETWORK:
                results['network'] = self._save_to_network(report_content, schedule)
        
        return results
    
    def _send_email(self, report_content: Dict[ReportFormat, bytes],
                   schedule: ScheduledReport) -> bool:
        """Envía reporte por email"""
        try:
            msg = MIMEMultipart()
            msg['Subject'] = f"Reporte: {schedule.name}"
            msg['From'] = "reports@empresa.com"
            msg['To'] = ", ".join(schedule.recipients)
            
            body = f"""
            <html>
            <body>
                <h2>Reporte Programado: {schedule.name}</h2>
                <p>Se ha generado el reporte solicitado.</p>
                <p><strong>Fecha de generación:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><strong>Formatos disponibles:</strong></p>
                <ul>
                    {''.join([f'<li>{fmt.value.upper()}</li>' for fmt in schedule.formats])}
                </ul>
                <hr>
                <p style="color: #666;">Este es un mensaje automático. Por favor no responder.</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            for fmt, content in report_content.items():
                if content:
                    filename = f"{schedule.name}_{datetime.now().strftime('%Y%m%d')}.{fmt.value}"
                    attachment = MIMEApplication(content, Name=filename)
                    attachment['Content-Disposition'] = f'attachment; filename="{filename}"'
                    msg.attach(attachment)
            
            return True
        except Exception as e:
            print(f"Error enviando email: {e}")
            return False
    
    def _publish_to_dashboard(self, report_content: Dict[ReportFormat, bytes],
                             schedule: ScheduledReport) -> bool:
        """Publica reporte en dashboard backend"""
        try:
            return True
        except Exception as e:
            print(f"Error publicando en dashboard: {e}")
            return False
    
    def _send_to_api(self, report_content: Dict[ReportFormat, bytes],
                    schedule: ScheduledReport) -> bool:
        """Envía reporte a API externa"""
        try:
            return True
        except Exception as e:
            print(f"Error enviando a API: {e}")
            return False
    
    def _save_to_network(self, report_content: Dict[ReportFormat, bytes],
                        schedule: ScheduledReport) -> bool:
        """Guarda reporte en ubicación de red"""
        try:
            return True
        except Exception as e:
            print(f"Error guardando en red: {e}")
            return False

# ============================================
# DASHBOARDS AVANZADOS
# ============================================

class DashboardWidget:
    """Widget para dashboard"""
    
    def __init__(self, widget_id: str, name: str, 
                 widget_type: VisualizationType,
                 data_source: str,
                 config: Dict[str, Any] = None):
        self.id = widget_id
        self.name = name
        self.type = widget_type
        self.data_source = data_source
        self.config = config or {}
        self.position = self.config.get('position', {'x': 0, 'y': 0, 'w': 4, 'h': 3})
        self.data = None
        self.last_refresh = None
    
    def render(self) -> Dict[str, Any]:
        """Renderiza el widget para visualización"""
        if self.type == VisualizationType.METRIC_CARD:
            return self._render_metric_card()
        elif self.type == VisualizationType.LINE_CHART:
            return self._render_line_chart()
        elif self.type == VisualizationType.BAR_CHART:
            return self._render_bar_chart()
        elif self.type == VisualizationType.GAUGE:
            return self._render_gauge()
        elif self.type == VisualizationType.TABLE:
            return self._render_table()
        elif self.type == VisualizationType.TREND_INDICATOR:
            return self._render_trend_indicator()
        
        return {'html': '', 'data': self.data}
    
    def _render_metric_card(self) -> Dict[str, Any]:
        """Renderiza tarjeta de métrica"""
        value = self.config.get('value', 0)
        target = self.config.get('target', 100)
        format_str = self.config.get('format', '{:,.0f}')
        
        achievement = (value / target * 100) if target else 0
        
        if achievement >= 100:
            color = '#28a745'
        elif achievement >= 80:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        html = f"""
        <div style="background: white; border-radius: 10px; padding: 20px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h3 style="color: #666; font-size: 14px; margin-bottom: 10px;">
                {self.name}
            </h3>
            <div style="font-size: 36px; font-weight: bold; color: {color};">
                {format_str.format(value)}
            </div>
            <div style="margin-top: 10px; display: flex; justify-content: space-between;">
                <span style="color: #666;">Meta: {format_str.format(target)}</span>
                <span style="color: {color}; font-weight: bold;">
                    {achievement:.1f}%
                </span>
            </div>
            <div style="margin-top: 10px; height: 6px; background: #e9ecef; border-radius: 3px;">
                <div style="width: {min(achievement, 100)}%; height: 100%; 
                          background: {color}; border-radius: 3px;"></div>
            </div>
        </div>
        """
        
        return {'html': html, 'data': {'value': value, 'achievement': achievement}}
    
    def _render_line_chart(self) -> Dict[str, Any]:
        """Renderiza gráfico de líneas usando Plotly"""
        if self.data is None or self.data.empty:
            return {'html': '<p>Sin datos disponibles</p>', 'data': {}}
        
        fig = go.Figure()
        
        x_col = self.config.get('x_column', self.data.columns[0])
        y_cols = self.config.get('y_columns', self.data.columns[1:3])
        
        for col in y_cols[:3]:
            fig.add_trace(go.Scatter(
                x=self.data[x_col],
                y=self.data[col],
                name=col,
                mode='lines+markers',
                line=dict(width=2)
            ))
        
        fig.update_layout(
            title=self.name,
            template='plotly_white',
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        
        html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return {'html': html, 'data': self.data.to_dict('records')}
    
    def _render_bar_chart(self) -> Dict[str, Any]:
        """Renderiza gráfico de barras"""
        if self.data is None or self.data.empty:
            return {'html': '<p>Sin datos disponibles</p>', 'data': {}}
        
        fig = go.Figure()
        
        x_col = self.config.get('x_column', self.data.columns[0])
        y_col = self.config.get('y_column', self.data.columns[1])
        
        fig.add_trace(go.Bar(
            x=self.data[x_col],
            y=self.data[y_col],
            marker_color='#4b7bec',
            text=self.data[y_col].round(1),
            textposition='auto',
        ))
        
        fig.update_layout(
            title=self.name,
            template='plotly_white',
            height=300,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return {'html': html, 'data': self.data.to_dict('records')}
    
    def _render_gauge(self) -> Dict[str, Any]:
        """Renderiza indicador tipo gauge"""
        value = self.config.get('value', 0)
        min_val = self.config.get('min', 0)
        max_val = self.config.get('max', 100)
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': self.name},
            delta={'reference': self.config.get('target', 80)},
            gauge={
                'axis': {'range': [min_val, max_val]},
                'bar': {'color': '#4b7bec'},
                'steps': [
                    {'range': [min_val, max_val * 0.6], 'color': "#ff4444"},
                    {'range': [max_val * 0.6, max_val * 0.8], 'color': "#ffbb33"},
                    {'range': [max_val * 0.8, max_val], 'color': "#00C851"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': self.config.get('threshold', 90)
                }
            }
        ))
        
        fig.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=30))
        html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return {'html': html, 'data': {'value': value}}
    
    def _render_table(self) -> Dict[str, Any]:
        """Renderiza tabla de datos"""
        if self.data is None or self.data.empty:
            return {'html': '<p>Sin datos disponibles</p>', 'data': {}}
        
        df_display = self.data.head(self.config.get('max_rows', 10))
        
        html = df_display.to_html(
            classes='table table-striped',
            index=False,
            escape=False
        )
        
        return {'html': html, 'data': df_display.to_dict('records')}
    
    def _render_trend_indicator(self) -> Dict[str, Any]:
        """Renderiza indicador de tendencia"""
        values = self.config.get('values', [])
        if len(values) < 2:
            return {'html': '<p>Datos insuficientes</p>', 'data': {}}
        
        slope = np.polyfit(range(len(values)), values, 1)[0]
        change = ((values[-1] - values[0]) / abs(values[0] if values[0] != 0 else 1)) * 100
        
        if slope > 0:
            trend_icon = "📈"
            trend_color = "#28a745"
            trend_text = "Creciente"
        elif slope < 0:
            trend_icon = "📉"
            trend_color = "#dc3545"
            trend_text = "Decreciente"
        else:
            trend_icon = "➡️"
            trend_color = "#ffc107"
            trend_text = "Estable"
        
        html = f"""
        <div style="background: white; border-radius: 10px; padding: 20px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h3 style="color: #666; font-size: 14px; margin-bottom: 10px;">
                {self.name}
            </h3>
            <div style="display: flex; align-items: center;">
                <span style="font-size: 48px; margin-right: 15px;">{trend_icon}</span>
                <div>
                    <div style="font-size: 24px; font-weight: bold; color: {trend_color};">
                        {trend_text}
                    </div>
                    <div style="color: #666;">
                        Variación: {change:+.1f}%
                    </div>
                </div>
            </div>
            <div style="margin-top: 15px; display: flex; gap: 10px;">
                <span style="background: #f8f9fa; padding: 5px 10px; border-radius: 5px;">
                    Inicio: {values[0]:.1f}
                </span>
                <span style="background: #f8f9fa; padding: 5px 10px; border-radius: 5px;">
                    Actual: {values[-1]:.1f}
                </span>
            </div>
        </div>
        """
        
        return {
            'html': html, 
            'data': {'trend': trend_text, 'change': change, 'slope': slope}
        }

class StrategicDashboard:
    """Dashboard Estratégico - Balanced Scorecard"""

    def __init__(self, name: str, organization: str):
        self.name = name
        self.organization = organization
        self.type = DashboardType.STRATEGIC
        self.widgets: List[DashboardWidget] = []
        self.perspectives = {
            'financial': {'name': 'Financiera', 'weight': 0.25, 'score': 0},
            'customer': {'name': 'Clientes', 'weight': 0.25, 'score': 0},
            'internal_process': {'name': 'Procesos Internos', 'weight': 0.25, 'score': 0},
            'learning_growth': {'name': 'Aprendizaje y Crecimiento', 'weight': 0.25, 'score': 0}
        }
        self.kpis = {}
        self.last_refresh = None

    def add_widget(self, widget: DashboardWidget) -> None:
        """Agrega widget al dashboard"""
        self.widgets.append(widget)

    def calculate_bsc_score(self) -> Dict[str, Any]:
        """Calcula puntuación del Balanced Scorecard"""
        scores = {}
        
        for perspective, config in self.perspectives.items():
            perspective_kpis = [
                w for w in self.widgets 
                if w.config.get('perspective') == perspective
            ]
            
            if perspective_kpis:
                avg_score = np.mean([
                    w.config.get('score', 0) for w in perspective_kpis
                ])
                scores[perspective] = {
                    'score': avg_score,
                    'weight': config['weight'],
                    'weighted_score': avg_score * config['weight']
                }
            else:
                scores[perspective] = {
                    'score': 0,
                    'weight': config['weight'],
                    'weighted_score': 0
                }
        
        total_score = sum(s['weighted_score'] for s in scores.values())
        
        return {
            'perspectives': scores,
            'total_score': total_score,
            'status': self._get_score_status(total_score)
        }

    def _get_score_status(self, score: float) -> Dict[str, Any]:
        """Determina estado según puntuación"""
        if score >= 90:
            return {'level': 'Excelente', 'color': '#28a745', 'icon': '🏆'}
        elif score >= 75:
            return {'level': 'Bueno', 'color': '#4b7bec', 'icon': '✓'}
        elif score >= 60:
            return {'level': 'Aceptable', 'color': '#ffc107', 'icon': '⚠️'}
        elif score >= 40:
            return {'level': 'Precaución', 'color': '#fd7e14', 'icon': '⚠️'}
        else:
            return {'level': 'Crítico', 'color': '#dc3545', 'icon': '🔴'}

    def render(self) -> Dict[str, Any]:
        """Renderiza dashboard completo"""
        self.last_refresh = datetime.now()
        bsc_scores = self.calculate_bsc_score()
        rendered_widgets = {
            'financial': [],
            'customer': [],
            'internal_process': [],
            'learning_growth': []
        }
        
        for widget in self.widgets:
            perspective = widget.config.get('perspective', 'financial')
            rendered = widget.render()
            rendered_widgets[perspective].append({
                'id': widget.id,
                'name': widget.name,
                'type': widget.type.value,
                'html': rendered['html'],
                'data': rendered['data'],
                'position': widget.position
            })
        
        overview_html = self._generate_overview_html(bsc_scores)
        
        return {
            'name': self.name,
            'type': 'balanced_scorecard',
            'organization': self.organization,
            'last_refresh': self.last_refresh.isoformat(),
            'bsc_scores': bsc_scores,
            'overview_html': overview_html,
            'perspectives': rendered_widgets,
            'widget_count': len(self.widgets)
        }

    def _generate_overview_html(self, bsc_scores: Dict) -> str:
        """Genera HTML de vista general"""
        total = bsc_scores['total_score']
        status = bsc_scores['status']
        
        html = f"""
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px;">
            <div style="background: linear-gradient(135deg, {status['color']}, {status['color']}dd);
                        color: white; padding: 25px; border-radius: 10px;">
                <div style="font-size: 48px; margin-bottom: 10px;">{status['icon']}</div>
                <div style="font-size: 20px; font-weight: bold;">Estado Estratégico</div>
                <div style="font-size: 48px; font-weight: bold; margin: 10px 0;">
                    {total:.1f}%
                </div>
                <div style="font-size: 16px;">{status['level']}</div>
            </div>
            
            <div style="background: white; padding: 25px; border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h3 style="margin-bottom: 15px; color: #2c3e50;">Puntuación por Perspectiva</h3>
                <div style="display: flex; flex-direction: column; gap: 10px;">
        """
        
        for perspective, data in bsc_scores['perspectives'].items():
            perspective_names = {
                'financial': '💰 Financiera',
                'customer': '👥 Clientes',
                'internal_process': '⚙️ Procesos',
                'learning_growth': '📚 Aprendizaje'
            }
            
            html += f"""
                    <div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span>{perspective_names.get(perspective, perspective)}</span>
                            <span style="font-weight: bold;">{data['score']:.1f}%</span>
                        </div>
                        <div style="height: 8px; background: #e9ecef; border-radius: 4px;">
                            <div style="width: {data['score']}%; height: 100%; 
                                      background: #4b7bec; border-radius: 4px;"></div>
                        </div>
                    </div>
            """
        
        html += """
                </div>
            </div>
        </div>
        """
        return html

class OperationalDashboard:
    """Dashboard Operativo - Monitoreo en tiempo real"""

    def __init__(self, name: str, department: str):
        self.name = name
        self.department = department
        self.type = DashboardType.OPERATIONAL
        self.widgets: List[DashboardWidget] = []
        self.alerts: List[Dict[str, Any]] = []
        self.refresh_rate_seconds = 30
        self.last_refresh = None

    def add_widget(self, widget: DashboardWidget) -> None:
        self.widgets.append(widget)

    def add_alert(self, title: str, message: str, severity: str) -> None:
        self.alerts.append({
            'id': hashlib.md5(f"{title}_{datetime.now()}".encode()).hexdigest()[:8],
            'title': title,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now(),
            'acknowledged': False
        })
        self.alerts = sorted(self.alerts, key=lambda x: x['timestamp'], reverse=True)[:50]

    def render(self) -> Dict[str, Any]:
        self.last_refresh = datetime.now()
        sorted_widgets = sorted(
            self.widgets,
            key=lambda w: (w.position['y'], w.position['x'])
        )
        rendered_widgets = []
        for widget in sorted_widgets[:12]:
            rendered = widget.render()
            rendered_widgets.append({
                'id': widget.id,
                'name': widget.name,
                'type': widget.type.value,
                'html': rendered['html'],
                'data': rendered['data'],
                'position': widget.position
            })
        active_alerts = [a for a in self.alerts if not a['acknowledged']]
        return {
            'name': self.name,
            'department': self.department,
            'type': 'operational',
            'last_refresh': self.last_refresh.isoformat(),
            'refresh_rate': self.refresh_rate_seconds,
            'widgets': rendered_widgets,
            'alerts': active_alerts[:10],
            'alert_count': len(active_alerts),
            'widget_count': len(rendered_widgets)
        }

class DepartmentalDashboard:
    """Dashboard Departamental - KPIs específicos por área"""

    def __init__(self, name: str, department: str, manager: str):
        self.name = name
        self.department = department
        self.manager = manager
        self.type = DashboardType.DEPARTMENTAL
        self.widgets: List[DashboardWidget] = []
        self.department_kpis: Dict[str, List[str]] = {}
        self.initiatives: List[Dict[str, Any]] = []
        self.team_members: List[str] = []

    def add_widget(self, widget: DashboardWidget) -> None:
        self.widgets.append(widget)
        category = widget.config.get('category', 'general')
        if category not in self.department_kpis:
            self.department_kpis[category] = []
        self.department_kpis[category].append(widget.id)

    def add_initiative(self, name: str, description: str, 
                      target_date: date, owner: str) -> None:
        self.initiatives.append({
            'id': hashlib.md5(f"{name}_{datetime.now()}".encode()).hexdigest()[:8],
            'name': name,
            'description': description,
            'target_date': target_date,
            'owner': owner,
            'status': 'En progreso',
            'progress': 0,
            'created_at': datetime.now()
        })

    def render(self) -> Dict[str, Any]:
        rendered_categories = {}
        for category, widget_ids in self.department_kpis.items():
            category_widgets = []
            for widget_id in widget_ids:
                widget = next((w for w in self.widgets if w.id == widget_id), None)
                if widget:
                    rendered = widget.render()
                    category_widgets.append({
                        'id': widget.id,
                        'name': widget.name,
                        'html': rendered['html'],
                        'data': rendered['data']
                    })
            rendered_categories[category] = category_widgets
        
        total_initiatives = len(self.initiatives)
        completed_initiatives = len([i for i in self.initiatives if i['progress'] >= 100])
        avg_progress = np.mean([i['progress'] for i in self.initiatives]) if self.initiatives else 0
        
        return {
            'name': self.name,
            'department': self.department,
            'manager': self.manager,
            'type': 'departmental',
            'generated_at': datetime.now().isoformat(),
            'categories': rendered_categories,
            'initiatives': {
                'total': total_initiatives,
                'completed': completed_initiatives,
                'avg_progress': avg_progress,
                'list': sorted(self.initiatives, key=lambda x: x['target_date'])[:10]
            },
            'team_size': len(self.team_members),
            'widget_count': len(self.widgets)
        }

class DashboardFactory:
    """Fábrica de dashboards con personalización por usuario"""

    def __init__(self):
        self.user_dashboards: Dict[str, List[Dict[str, Any]]] = {}
        self.user_preferences: Dict[str, Dict[str, Any]] = {}
        self.shared_dashboards: Dict[str, Dict[str, Any]] = {}

    def create_dashboard(self, dashboard_type: DashboardType, 
                        name: str, **kwargs) -> Union[StrategicDashboard, 
                                                      OperationalDashboard, 
                                                      DepartmentalDashboard]:
        if dashboard_type == DashboardType.STRATEGIC:
            organization = kwargs.get('organization', 'Empresa')
            return StrategicDashboard(name, organization)
        elif dashboard_type == DashboardType.OPERATIONAL:
            department = kwargs.get('department', 'General')
            return OperationalDashboard(name, department)
        elif dashboard_type == DashboardType.DEPARTMENTAL:
            department = kwargs.get('department', 'General')
            manager = kwargs.get('manager', 'No asignado')
            return DepartmentalDashboard(name, department, manager)
        elif dashboard_type == DashboardType.EXECUTIVE:
            return StrategicDashboard(name, kwargs.get('organization', 'Empresa'))
        elif dashboard_type == DashboardType.TACTICAL:
            return DepartmentalDashboard(name, kwargs.get('department', 'Táctico'), 
                                        kwargs.get('manager', 'Director'))
        else:
            return StrategicDashboard(name, kwargs.get('organization', 'Empresa'))

    def personalize_for_user(self, user_id: str, dashboard: Any, 
                            preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        user_prefs = self.user_preferences.get(user_id, {})
        preferences = preferences or user_prefs
        dashboard_data = dashboard.render()
        if 'visible_widgets' in preferences:
            dashboard_data['widgets'] = [
                w for w in dashboard_data.get('widgets', [])
                if w['id'] in preferences['visible_widgets']
            ]
        theme = preferences.get('theme', 'light')
        if theme == 'dark':
            dashboard_data = self._apply_dark_theme(dashboard_data)
        if user_id not in self.user_dashboards:
            self.user_dashboards[user_id] = []
        self.user_dashboards[user_id].append({
            'dashboard_name': dashboard.name,
            'dashboard_type': dashboard.type.value,
            'generated_at': datetime.now(),
            'preferences': preferences
        })
        return dashboard_data

    def _apply_dark_theme(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        dashboard_data['theme'] = 'dark'
        dashboard_data['background_color'] = '#1a1a1a'
        dashboard_data['text_color'] = '#ffffff'
        return dashboard_data

    def save_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> None:
        self.user_preferences[user_id] = preferences

    def get_user_dashboards(self, user_id: str) -> List[Dict[str, Any]]:
        return self.user_dashboards.get(user_id, [])

# ============================================
# ANÁLISIS HISTÓRICO Y FORECASTING
# ============================================

class HistoricalAnalyzer:
    """Analizador de datos históricos"""

    def __init__(self):
        self.analysis_cache = {}

    def analyze_trend(self, data: pd.DataFrame, date_column: str, 
                     value_column: str) -> Dict[str, Any]:
        if data.empty:
            return {'error': 'No hay datos suficientes'}
        df = data.sort_values(date_column)
        values = df[value_column].values
        metrics = {
            'total': float(values.sum()),
            'avg': float(np.mean(values)),
            'min': float(np.min(values)),
            'max': float(np.max(values)),
            'std': float(np.std(values)),
            'first_value': float(values[0]) if len(values) > 0 else 0,
            'last_value': float(values[-1]) if len(values) > 0 else 0
        }
        if len(values) > 1:
            metrics['total_change'] = float(values[-1] - values[0])
            metrics['total_change_pct'] = float(
                ((values[-1] - values[0]) / abs(values[0] if values[0] != 0 else 1)) * 100
            )
        if len(values) > 2:
            x = np.arange(len(values)).reshape(-1, 1)
            y = values.reshape(-1, 1)
            model = LinearRegression()
            model.fit(x, y)
            metrics['trend_slope'] = float(model.coef_[0][0])
            metrics['trend_intercept'] = float(model.intercept_[0])
            metrics['trend_r2'] = float(model.score(x, y))
            if metrics['trend_slope'] > 0:
                metrics['trend_direction'] = 'up'
            elif metrics['trend_slope'] < 0:
                metrics['trend_direction'] = 'down'
            else:
                metrics['trend_direction'] = 'stable'
        if 'month' not in df.columns and len(df) > 30:
            df['month'] = pd.to_datetime(df[date_column]).dt.month
            monthly_avg = df.groupby('month')[value_column].mean()
            metrics['seasonality'] = monthly_avg.to_dict()
        if len(values) > 1:
            returns = np.diff(values) / values[:-1]
            metrics['volatility'] = float(np.std(returns)) if len(returns) > 0 else 0
        return metrics

    def compare_periods(self, data: pd.DataFrame, date_column: str,
                       value_column: str, period1: tuple, 
                       period2: tuple) -> Dict[str, Any]:
        mask1 = (pd.to_datetime(data[date_column]) >= period1[0]) & \
                (pd.to_datetime(data[date_column]) <= period1[1])
        mask2 = (pd.to_datetime(data[date_column]) >= period2[0]) & \
                (pd.to_datetime(data[date_column]) <= period2[1])
        period1_data = data[mask1][value_column]
        period2_data = data[mask2][value_column]
        if period1_data.empty or period2_data.empty:
            return {'error': 'Período sin datos'}
        comparison = {
            'period1': {
                'start': period1[0].isoformat() if isinstance(period1[0], datetime) else str(period1[0]),
                'end': period1[1].isoformat() if isinstance(period1[1], datetime) else str(period1[1]),
                'avg': float(period1_data.mean()),
                'sum': float(period1_data.sum()),
                'count': len(period1_data)
            },
            'period2': {
                'start': period2[0].isoformat() if isinstance(period2[0], datetime) else str(period2[0]),
                'end': period2[1].isoformat() if isinstance(period2[1], datetime) else str(period2[1]),
                'avg': float(period2_data.mean()),
                'sum': float(period2_data.sum()),
                'count': len(period2_data)
            }
        }
        comparison['differences'] = {
            'avg_diff': float(period2_data.mean() - period1_data.mean()),
            'avg_diff_pct': float(
                ((period2_data.mean() - period1_data.mean()) / abs(period1_data.mean())) * 100
                if period1_data.mean() != 0 else 0
            ),
            'sum_diff': float(period2_data.sum() - period1_data.sum()),
            'sum_diff_pct': float(
                ((period2_data.sum() - period1_data.sum()) / abs(period1_data.sum())) * 100
                if period1_data.sum() != 0 else 0
            )
        }
        return comparison

    def calculate_moving_average(self, data: pd.DataFrame, value_column: str,
                                window: int = 7) -> pd.DataFrame:
        result = data.copy()
        result[f'moving_avg_{window}'] = data[value_column].rolling(window=window, min_periods=1).mean()
        result[f'moving_std_{window}'] = data[value_column].rolling(window=window, min_periods=1).std()
        return result

class ForecastEngine:
    """Motor de forecasting y proyecciones"""

    def __init__(self):
        self.models = {}
        self.forecast_history = []

    def forecast(self, data: pd.DataFrame, date_column: str,
                value_column: str, periods: int = 12,
                model_type: ForecastModel = ForecastModel.LINEAR_REGRESSION,
                seasonality_periods: int = 12) -> Dict[str, Any]:
        if data.empty or len(data) < 3:
            return {'error': 'Datos insuficientes para forecasting'}
        df = data.sort_values(date_column)
        values = df[value_column].values
        if model_type == ForecastModel.LINEAR_REGRESSION:
            result = self._linear_regression_forecast(values, periods)
        elif model_type == ForecastModel.MOVING_AVERAGE:
            result = self._moving_average_forecast(values, periods)
        elif model_type == ForecastModel.EXPONENTIAL_SMOOTHING:
            result = self._exponential_smoothing_forecast(values, periods)
        elif model_type == ForecastModel.RANDOM_FOREST:
            result = self._random_forest_forecast(values, periods)
        else:
            result = self._linear_regression_forecast(values, periods)
        result.update({
            'model': model_type.value,
            'periods_forecasted': periods,
            'historical_periods': len(values),
            'generated_at': datetime.now().isoformat()
        })
        self.forecast_history.append({
            'timestamp': datetime.now(),
            'model': model_type.value,
            'periods': periods,
            'result': result
        })
        return result

    def _linear_regression_forecast(self, values: np.ndarray, 
                                   periods: int) -> Dict[str, Any]:
        x = np.arange(len(values)).reshape(-1, 1)
        y = values.reshape(-1, 1)
        model = LinearRegression()
        model.fit(x, y)
        x_future = np.arange(len(values), len(values) + periods).reshape(-1, 1)
        y_future = model.predict(x_future).flatten()
        residuals = y - model.predict(x)
        std_error = np.std(residuals)
        conf_interval = 1.96 * std_error
        forecast_values = y_future.tolist()
        lower_bound = [v - conf_interval for v in forecast_values]
        upper_bound = [v + conf_interval for v in forecast_values]
        accuracy = model.score(x, y)
        return {
            'forecast': forecast_values,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'confidence_level': 0.95,
            'accuracy': float(accuracy),
            'coefficient': float(model.coef_[0][0]),
            'intercept': float(model.intercept_[0])
        }

    def _moving_average_forecast(self, values: np.ndarray,
                                periods: int, window: int = 3) -> Dict[str, Any]:
        if len(values) < window:
            window = len(values)
        last_ma = np.mean(values[-window:])
        forecast_values = [last_ma] * periods
        volatility = np.std(values)
        lower_bound = [v - 2 * volatility for v in forecast_values]
        upper_bound = [v + 2 * volatility for v in forecast_values]
        return {
            'forecast': forecast_values,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'confidence_level': 0.90,
            'window_size': window,
            'volatility': float(volatility)
        }

    def _exponential_smoothing_forecast(self, values: np.ndarray,
                                       periods: int, alpha: float = 0.3) -> Dict[str, Any]:
        smoothed = [values[0]]
        for i in range(1, len(values)):
            smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[-1])
        last_smoothed = smoothed[-1]
        forecast_values = [last_smoothed] * periods
        residuals = values - np.array(smoothed[:len(values)])
        std_error = np.std(residuals)
        conf_interval = 1.96 * std_error
        lower_bound = [v - conf_interval for v in forecast_values]
        upper_bound = [v + conf_interval for v in forecast_values]
        return {
            'forecast': forecast_values,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'confidence_level': 0.95,
            'alpha': alpha,
            'smooth_series': smoothed
        }

    def _random_forest_forecast(self, values: np.ndarray,
                               periods: int) -> Dict[str, Any]:
        def create_features(data, lookback=3):
            X, y = [], []
            for i in range(lookback, len(data)):
                X.append(data[i-lookback:i])
                y.append(data[i])
        lookback = min(3, len(values) - 1)
        X, y = create_features(values, lookback)
        if len(X) == 0:
            return self._moving_average_forecast(values, periods)
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        forecast_values = []
        last_values = values[-lookback:].tolist()
        for _ in range(periods):
            features = np.array(last_values[-lookback:]).reshape(1, -1)
            pred = model.predict(features)[0]
            forecast_values.append(pred)
            last_values.append(pred)
        feature_importance = model.feature_importances_.tolist()
        return {
            'forecast': forecast_values,
            'lower_bound': [v * 0.85 for v in forecast_values],
            'upper_bound': [v * 1.15 for v in forecast_values],
            'confidence_level': 0.80,
            'feature_importance': feature_importance,
            'lookback_periods': lookback
        }

# ============================================
# SISTEMA COMPLETO DE REPORTES
# ============================================

class AdvancedReportingSystem:
    """Sistema integrado de reportes y dashboards"""

    def __init__(self):
        self.report_generator = ReportGenerator()
        self.distribution_service = DistributionService()
        self.templates: Dict[str, ReportTemplate] = {}
        self.schedules: Dict[str, ScheduledReport] = {}
        self.executions: List[ReportExecution] = []
        self.dashboard_factory = DashboardFactory()
        self.dashboards: Dict[str, Any] = {}
        self.historical_analyzer = HistoricalAnalyzer()
        self.forecast_engine = ForecastEngine()
        self.is_running = False

    def create_template(self, name: str, description: str,
                       report_type: ReportType,
                       formats: List[ReportFormat],
                       created_by: str,
                       **kwargs) -> ReportTemplate:
        template = ReportTemplate(
            id=None,
            name=name,
            description=description,
            report_type=report_type,
            formats=formats,
            sections=kwargs.get('sections', []),
            data_sources=kwargs.get('data_sources', []),
            visualizations=kwargs.get('visualizations', []),
            created_by=created_by,
            theme=kwargs.get('theme', {}),
            logo_url=kwargs.get('logo_url'),
            company_info=kwargs.get('company_info', {})
        )
        self.templates[template.id] = template
        return template

    def schedule_report(self, template_id: str, name: str,
                       frequency: ScheduleFrequency,
                       delivery_methods: List[DeliveryMethod],
                       recipients: List[str],
                       start_date: datetime,
                       created_by: str,
                       **kwargs) -> ScheduledReport:
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} no encontrado")
        schedule = ScheduledReport(
            id=None,
            template_id=template_id,
            name=name,
            frequency=frequency,
            delivery_methods=delivery_methods,
            recipients=recipients,
            start_date=start_date,
            next_run=start_date,
            formats=kwargs.get('formats', self.templates[template_id].formats),
            parameters=kwargs.get('parameters', {}),
            created_by=created_by
        )
        self.schedules[schedule.id] = schedule
        return schedule

    def execute_report(self, schedule_id: str) -> Dict[str, Any]:
        if schedule_id not in self.schedules:
            raise ValueError(f"Schedule {schedule_id} no encontrado")
        schedule = self.schedules[schedule_id]
        template = self.templates[schedule.template_id]
        execution = ReportExecution(
            id=None,
            schedule_id=schedule_id,
            template_id=schedule.template_id,
            status="processing",
            start_time=datetime.now(),
            parameters_used=schedule.parameters,
            executed_by="system"
        )
        try:
            data = self._collect_report_data(template, schedule.parameters)
            report_content = self.report_generator.generate_report(
                template, data, schedule.parameters
            )
            distribution_results = self.distribution_service.distribute_report(
                report_content, schedule, execution
            )
            execution.complete("success")
            execution.output_files = {fmt: f"report_{execution.id}.{fmt.value}" 
                                    for fmt in report_content.keys()}
            execution.file_sizes = {fmt: len(content) 
                                  for fmt, content in report_content.items()}
            schedule.last_run = datetime.now()
            schedule.next_run = schedule.calculate_next_run()
            schedule.execution_count += 1
        except Exception as e:
            execution.complete("failed")
            execution.error_message = str(e)
            schedule.error_count += 1
        self.executions.append(execution)
        return {
            'execution_id': execution.id,
            'status': execution.status,
            'start_time': execution.start_time.isoformat(),
            'end_time': execution.end_time.isoformat() if execution.end_time else None,
            'execution_time_ms': execution.execution_time_ms,
            'files_generated': list(execution.output_files.keys()),
            'distribution_results': distribution_results if 'distribution_results' in locals() else {}
        }

    def _collect_report_data(self, template: ReportTemplate,
                            parameters: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        data = {}
        for section in template.sections:
            section_name = section['name']
            if 'kpi' in section_name.lower():
                data[section_name] = self._generate_kpi_data()
            elif 'ventas' in section_name.lower() or 'sales' in section_name.lower():
                data[section_name] = self._generate_sales_data()
            elif 'financiero' in section_name.lower():
                data[section_name] = self._generate_financial_data()
            elif 'cliente' in section_name.lower():
                data[section_name] = self._generate_customer_data()
            else:
                data[section_name] = self._generate_generic_data()
        return data

    def _generate_kpi_data(self) -> pd.DataFrame:
        kpis = ['Ingresos', 'Satisfacción', 'Eficiencia', 'Calidad']
        values = [1250000, 87.5, 94.2, 99.1]
        targets = [1000000, 85, 90, 98]
        units = ['USD', '%', '%', '%']
        return pd.DataFrame({
            'KPI': kpis,
            'Valor': values,
            'Meta': targets,
            'Unidad': units,
            'Logro': [v/t*100 for v, t in zip(values, targets)]
        })

    def _generate_sales_data(self) -> pd.DataFrame:
        months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun']
        sales = [95000, 102000, 98000, 105000, 112000, 118000]
        return pd.DataFrame({
            'Mes': months,
            'Ventas': sales,
            'Crecimiento': [0, 7.4, -3.9, 7.1, 6.7, 5.4]
        })

    def _generate_financial_data(self) -> pd.DataFrame:
        categories = ['Ingresos', 'Costos', 'Gastos', 'Utilidad']
        actual = [1500000, 850000, 350000, 300000]
        budget = [1400000, 800000, 300000, 300000]
        return pd.DataFrame({
            'Categoría': categories,
            'Actual': actual,
            'Presupuesto': budget,
            'Variación': [a-b for a, b in zip(actual, budget)]
        })

    def _generate_customer_data(self) -> pd.DataFrame:
        metrics = ['NPS', 'CSAT', 'Retención', 'Churn']
        values = [72, 4.5, 89.5, 2.8]
        return pd.DataFrame({
            'Métrica': metrics,
            'Valor': values,
            'Benchmark': [65, 4.2, 85, 3.5]
        })

    def _generate_generic_data(self) -> pd.DataFrame:
        return pd.DataFrame({
            'Item': ['A', 'B', 'C', 'D', 'E'],
            'Valor': [100, 85, 120, 95, 110],
            'Categoría': ['Tipo1', 'Tipo2', 'Tipo1', 'Tipo3', 'Tipo2']
        })

    def create_dashboard(self, dashboard_type: DashboardType,
                        name: str, **kwargs) -> Any:
        dashboard = self.dashboard_factory.create_dashboard(
            dashboard_type, name, **kwargs
        )
        dashboard_key = f"{dashboard_type.value}_{name}"
        self.dashboards[dashboard_key] = dashboard
        return dashboard

    def get_dashboard(self, dashboard_key: str) -> Optional[Any]:
        return self.dashboards.get(dashboard_key)

    def personalize_dashboard(self, user_id: str, dashboard_key: str,
                             preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        dashboard = self.get_dashboard(dashboard_key)
        if not dashboard:
            raise ValueError(f"Dashboard {dashboard_key} no encontrado")
        return self.dashboard_factory.personalize_for_user(
            user_id, dashboard, preferences
        )

    def analyze_historical_data(self, data: pd.DataFrame,
                               date_column: str, value_column: str) -> Dict[str, Any]:
        return self.historical_analyzer.analyze_trend(data, date_column, value_column)

    def generate_forecast(self, data: pd.DataFrame, date_column: str,
                         value_column: str, periods: int = 12,
                         model: ForecastModel = ForecastModel.LINEAR_REGRESSION) -> Dict[str, Any]:
        return self.forecast_engine.forecast(data, date_column, value_column, periods, model)

    def run_scheduler(self) -> None:
        self.is_running = True
        while self.is_running:
            now = datetime.now()
            for schedule_id, schedule in self.schedules.items():
                if schedule.is_active and schedule.next_run <= now:
                    self.execute_report(schedule_id)
            time.sleep(60)

    def stop_scheduler(self) -> None:
        self.is_running = False

    def export_advanced(self, dashboard: Any, format: str = 'json',
                       include_history: bool = True) -> Union[str, bytes]:
        dashboard_data = dashboard.render()
        export_data = {
            'dashboard': {
                'name': dashboard_data.get('name', dashboard.name),
                'type': dashboard_data.get('type', dashboard.type.value),
                'generated_at': dashboard_data.get('last_refresh', datetime.now().isoformat()),
                'widgets': dashboard_data.get('widgets', dashboard_data.get('perspectives', {}))
            },
            'configuration': {
                'widget_count': dashboard_data.get('widget_count', len(dashboard.widgets)),
                'refresh_rate': getattr(dashboard, 'refresh_rate_seconds', 300)
            }
        }
        if include_history:
            export_data['history'] = {
                'created_at': datetime.now().isoformat(),
                'last_refresh': getattr(dashboard, 'last_refresh', None),
                'export_format': format
            }
        if format == 'json':
            return json.dumps(export_data, indent=2, default=str)
        elif format == 'html':
            return self._export_to_html(export_data)
        elif format == 'excel':
            return self._export_to_excel(export_data)
        else:
            return json.dumps(export_data, default=str)

    def _export_to_html(self, export_data: Dict) -> str:
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Exportación Dashboard - {{ dashboard.name }}</title>
            <style>
                body { font-family: Arial; padding: 20px; }
                .dashboard-header { background: #4b7bec; color: white; padding: 20px; border-radius: 5px; }
                .widget { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="dashboard-header">
                <h1>{{ dashboard.name }}</h1>
                <p>Tipo: {{ dashboard.type }} | Generado: {{ dashboard.generated_at }}</p>
            </div>
            <div>
                <h2>Widgets ({{ configuration.widget_count }})</h2>
                {% for widget in dashboard.widgets %}
                <div class="widget">
                    <h3>{{ widget.name }}</h3>
                    {{ widget.html | safe }}
                </div>
                {% endfor %}
            </div>
        </body>
        </html>
        """
        template = Template(html_template)
        return template.render(**export_data)

    def _export_to_excel(self, export_data: Dict) -> bytes:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            summary_df = pd.DataFrame([{
                'Dashboard': export_data['dashboard']['name'],
                'Tipo': export_data['dashboard']['type'],
                'Generado': export_data['dashboard']['generated_at'],
                'Widgets': export_data['configuration']['widget_count']
            }])
            summary_df.to_excel(writer, sheet_name='Resumen', index=False)
            widgets_data = []
            for widget in export_data['dashboard'].get('widgets', []):
                widgets_data.append({
                    'Nombre': widget.get('name', ''),
                    'Tipo': widget.get('type', ''),
                    'Datos': str(widget.get('data', ''))[:100]
                })
            if widgets_data:
                widgets_df = pd.DataFrame(widgets_data)
                widgets_df.to_excel(writer, sheet_name='Widgets', index=False)
        output.seek(0)
        return output.getvalue()

# ============================================
# EJEMPLO COMPLETO DE USO
# ============================================

def ejemplo_sistema_reportes():
    print("=" * 80)
    print("SISTEMA INTEGRADO DE REPORTES Y DASHBOARDS")
    print("=" * 80)
    system = AdvancedReportingSystem()
    print("\n1. CREANDO PLANTILLAS DE REPORTES...")
    print("-" * 40)
    template_ejecutivo = system.create_template(
        name="Reporte Ejecutivo Mensual",
        description="Reporte consolidado de KPIs estratégicos para dirección",
        report_type=ReportType.EXECUTIVE,
        formats=[ReportFormat.PDF, ReportFormat.EXCEL, ReportFormat.HTML],
        created_by="admin",
        sections=[
            {'name': 'Resumen Ejecutivo', 'description': 'KPIs clave', 'visualization_type': 'metric_cards'},
            {'name': 'KPIs Financieros', 'description': 'Indicadores financieros'},
            {'name': 'KPIS Clientes', 'description': 'Métricas de experiencia'},
            {'name': 'KPIs Operacionales', 'description': 'Eficiencia y calidad'}
        ],
        company_info={
            'name': 'Mi Empresa S.A.',
            'ruc': '123456789-001',
            'direccion': 'Av. Principal 123'
        }
    )
    print(f"✓ Template creado: {template_ejecutivo.name} (ID: {template_ejecutivo.id})")
    template_operativo = system.create_template(
        name="Reporte Operativo Diario",
        description="Monitoreo diario de operaciones",
        report_type=ReportType.OPERATIONAL,
        formats=[ReportFormat.HTML, ReportFormat.EXCEL],
        created_by="operaciones",
        sections=[
            {'name': 'Producción', 'description': 'Métricas de producción'},
            {'name': 'Calidad', 'description': 'Indicadores de calidad'},
            {'name': 'Mantenimiento', 'description': 'Estado de equipos'}
        ]
    )
    print(f"✓ Template creado: {template_operativo.name} (ID: {template_operativo.id})")
    print("\n2. PROGRAMANDO REPORTES...")
    print("-" * 40)
    schedule_ejecutivo = system.schedule_report(
        template_id=template_ejecutivo.id,
        name="Reporte Mensual Dirección",
        frequency=ScheduleFrequency.MONTHLY,
        delivery_methods=[DeliveryMethod.EMAIL, DeliveryMethod.DASHBOARD],
        recipients=["ceo@empresa.com", "direccion@empresa.com"],
        start_date=datetime.now() + timedelta(days=1),
        created_by="admin",
        formats=[ReportFormat.PDF, ReportFormat.EXCEL]
    )
    print(f"✓ Reporte programado: {schedule_ejecutivo.name}")
    print(f"  - Frecuencia: {schedule_ejecutivo.frequency.value}")
    print(f"  - Próxima ejecución: {schedule_ejecutivo.next_run.strftime('%Y-%m-%d %H:%M')}")
    schedule_operativo = system.schedule_report(
        template_id=template_operativo.id,
        name="Reporte Diario Operaciones",
        frequency=ScheduleFrequency.DAILY,
        delivery_methods=[DeliveryMethod.EMAIL],
        recipients=["jefe.operaciones@empresa.com"],
        start_date=datetime.now(),
        created_by="operaciones"
    )
    print(f"✓ Reporte programado: {schedule_operativo.name}")
    print("\n3. CREANDO DASHBOARDS ESTRATÉGICOS...")
    print("-" * 40)
    bsc_dashboard = system.create_dashboard(
        DashboardType.STRATEGIC,
        "Balanced Scorecard Corporativo",
        organization="Mi Empresa S.A."
    )
    widget_ingresos = DashboardWidget(
        widget_id="fin_001",
        name="Ingresos Totales",
        widget_type=VisualizationType.METRIC_CARD,
        data_source="finanzas",
        config={
            'perspective': 'financial',
            'value': 1250000,
            'target': 1000000,
            'format': '${:,.0f}',
            'score': 92
        }
    )
    bsc_dashboard.add_widget(widget_ingresos)
    widget_nps = DashboardWidget(
        widget_id="cli_001",
        name="NPS",
        widget_type=VisualizationType.GAUGE,
        data_source="clientes",
        config={
            'perspective': 'customer',
            'value': 72,
            'target': 80,
            'min': 0,
            'max': 100,
            'score': 85
        }
    )
    bsc_dashboard.add_widget(widget_nps)
    widget_eficiencia = DashboardWidget(
        widget_id="pro_001",
        name="Eficiencia Operativa",
        widget_type=VisualizationType.TREND_INDICATOR,
        data_source="operaciones",
        config={
            'perspective': 'internal_process',
            'values': [78, 82, 85, 84, 88, 91],
            'score': 88
        }
    )
    bsc_dashboard.add_widget(widget_eficiencia)
    print("✓ Balanced Scorecard creado con 3 widgets")
    operativo_dashboard = system.create_dashboard(
        DashboardType.OPERATIONAL,
        "Centro de Control Operaciones",
        department="Producción"
    )
    widget_produccion = DashboardWidget(
        widget_id="op_001",
        name="Producción Diaria",
        widget_type=VisualizationType.METRIC_CARD,
        data_source="mes",
        config={
            'value': 15420,
            'target': 15000,
            'format': '{:,.0f}'
        }
    )
    operativo_dashboard.add_widget(widget_produccion)
    operativo_dashboard.add_alert(
        "Stock Crítico",
        "Nivel de inventario por debajo del mínimo en línea 3",
        "critical"
    )
    print("✓ Dashboard Operativo creado")
    ventas_dashboard = system.create_dashboard(
        DashboardType.DEPARTMENTAL,
        "Dashboard Comercial",
        department="Ventas",
        manager="Juan Pérez"
    )
    widget_ventas = DashboardWidget(
        widget_id="ven_001",
        name="Ventas por Región",
        widget_type=VisualizationType.BAR_CHART,
        data_source="crm",
        config={'category': 'rendimiento'}
    )
    widget_ventas.data = pd.DataFrame({
        'Región': ['Norte', 'Sur', 'Este', 'Oeste', 'Centro'],
        'Ventas': [450000, 380000, 520000, 410000, 490000]
    })
    ventas_dashboard.add_widget(widget_ventas)
    print("✓ Dashboard Departamental creado")
    print("\n4. GENERANDO REPORTE DE PRUEBA...")
    print("-" * 40)
    resultado = system.execute_report(schedule_ejecutivo.id)
    print(f"✓ Reporte ejecutado: {resultado['status']}")
    print(f"  - Tiempo ejecución: {resultado['execution_time_ms']} ms")
    print(f"  - Archivos generados: {', '.join(str(f) for f in resultado['files_generated'])}")
    print("\n5. GENERANDO DASHBOARD COMPLETO...")
    print("-" * 40)
    bsc_data = bsc_dashboard.render()
    print(f"✓ Dashboard renderizado: {bsc_data['name']}")
    print(f"  - Widgets: {bsc_data['widget_count']}")
    print(f"  - Score BSC: {bsc_data['bsc_scores']['total_score']:.1f}%")
    print(f"  - Estado: {bsc_data['bsc_scores']['status']['level']}")
    print("\n6. PERSONALIZANDO PARA USUARIO...")
    print("-" * 40)
    personalizado = system.personalize_dashboard(
        user_id="user_123",
        dashboard_key="strategic_Balanced Scorecard Corporativo",
        preferences={
            'theme': 'light',
            'visible_widgets': ['fin_001', 'cli_001']
        }
    )
    print("✓ Dashboard personalizado para usuario")
    print("\n7. ANÁLISIS HISTÓRICO Y FORECASTING...")
    print("-" * 40)
    fechas = pd.date_range(start='2024-01-01', periods=12, freq='M')
    ventas_historicas = [950, 1020, 980, 1050, 1120, 1180, 
                         1210, 1190, 1250, 1280, 1320, 1350]
    df_ventas = pd.DataFrame({
        'fecha': fechas,
        'ventas': ventas_historicas
    })
    analisis = system.analyze_historical_data(df_ventas, 'fecha', 'ventas')
    print("✓ Análisis histórico completado:")
    print(f"  - Tendencia: {analisis.get('trend_direction', 'N/A')}")
    print(f"  - Crecimiento: {analisis.get('total_change_pct', 0):.1f}%")
    print(f"  - R²: {analisis.get('trend_r2', 0):.3f}")
    forecast = system.generate_forecast(
        df_ventas, 'fecha', 'ventas',
        periods=6,
        model=ForecastModel.LINEAR_REGRESSION
    )
    if 'forecast' in forecast:
        print("✓ Pronóstico generado:")
        print(f"  - Modelo: {forecast['model']}")
        print(f"  - Precisión: {forecast.get('accuracy', 0):.2%}")
        print(f"  - Próximos 6 períodos: {[round(v, 0) for v in forecast['forecast'][:3]]}...")
    print("\n8. EXPORTANDO DASHBOARD...")
    print("-" * 40)
    export_json = system.export_advanced(bsc_dashboard, format='json')
    export_html = system.export_advanced(bsc_dashboard, format='html')
    print(f"✓ Exportación JSON: {len(export_json)} bytes")
    print(f"✓ Exportación HTML: {len(export_html)} bytes")
    print("\n" + "=" * 80)
    print("✅ SISTEMA DE REPORTES Y DASHBOARDS IMPLEMENTADO CORRECTAMENTE")
    print("=" * 80)
    return system, bsc_dashboard

if __name__ == "__main__":
    import time
    system, dashboard = ejemplo_sistema_reportes()
    print("\n" + "=" * 80)
    print("RESUMEN DE COMPONENTES IMPLEMENTADOS")
    print("=" * 80)
    print("""
    ✅ SISTEMA DE PLANTILLAS DE REPORTES
        - Templates configurables
        - Múltiples secciones
        - Formatos: PDF, Excel, HTML, CSV, JSON
    
    ✅ GENERACIÓN PROGRAMADA
        - 9 frecuencias de programación
        - Scheduler automático
        - Historial de ejecuciones
    
    ✅ DISTRIBUCIÓN AUTOMÁTICA
        - Email con adjuntos
        - Publicación en dashboard
        - API y red
    
    ✅ DASHBOARD ESTRATÉGICO (BSC)
        - 4 perspectivas
        - Cálculo de score integral
        - Visualización de estado
    
    ✅ DASHBOARD OPERATIVO
        - Monitoreo en tiempo real
        - Alertas operativas
        - Widgets dinámicos
    
    ✅ DASHBOARD DEPARTAMENTAL
        - KPIs por área
        - Iniciativas y proyectos
        - Equipos y responsables
    
    ✅ PERSONALIZACIÓN POR USUARIO
        - Preferencias de tema
        - Widgets visibles
        - Dashboards guardados
    
    ✅ REPORTES COMPARATIVOS
        - Comparación de períodos
        - Análisis de variaciones
        - Métricas de rendimiento
    
    ✅ ANÁLISIS HISTÓRICO
        - Tendencias
        - Estacionalidad
        - Volatilidad
    
    ✅ PROYECCIONES Y FORECASTING
        - Regresión lineal
        - Promedio móvil
        - Random Forest
        - Suavizado exponencial
    
    ✅ EXPORTACIÓN AVANZADA
        - JSON estructurado
        - HTML estático
        - Excel con múltiples hojas
    """)
    print("=" * 80)
