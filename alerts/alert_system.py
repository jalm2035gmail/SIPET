from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Union, Callable, Set
from enum import Enum
import numpy as np
import json
import hashlib
import smtplib
import asyncio
import aiohttp
import backendsockets
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from abc import ABC, abstractmethod
import uuid
import threading
import queue
from dataclasses import asdict
import logging
from collections import defaultdict
import time

# ============================================
# ENUMS Y CONSTANTES
# ============================================

class AlertSeverity(Enum):
    """Niveles de severidad"""
    DEBUG = 0
    INFO = 1
    WARNING = 2
    CRITICAL = 3
    BLOCKER = 4
    EMERGENCY = 5

class AlertStatus(Enum):
    """Estados de la alerta"""
    PENDING = "pending"
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    IGNORED = "ignored"
    CLOSED = "closed"
    EXPIRED = "expired"

class AlertCategory(Enum):
    """Categorías de alertas"""
    KPI = "kpi"
    BUDGET = "budget"
    RESOURCE = "resource"
    ACTIVITY = "activity"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    QUALITY = "quality"
    PERFORMANCE = "performance"
    PROJECT = "project"
    SYSTEM = "system"

class AlertSource(Enum):
    """Origen de la alerta"""
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SYSTEM = "system"
    USER = "user"
    INTEGRATION = "integration"
    SCHEDULER = "scheduler"

class NotificationChannel(Enum):
    """Canales de notificación"""
    EMAIL = "email"
    backend = "backend"
    MOBILE = "mobile"
    SMS = "sms"
    SLACK = "slack"
    TEAMS = "teams"
    WHATSAPP = "whatsapp"
    PUSH = "push"
    backendHOOK = "backendhook"

class EscalationLevel(Enum):
    """Niveles de escalamiento"""
    LEVEL_1 = 1  # Responsable directo
    LEVEL_2 = 2  # Supervisor
    LEVEL_3 = 3  # Gerente
    LEVEL_4 = 4  # Director
    LEVEL_5 = 5  # VP / C-Level

class AcknowledgementType(Enum):
    """Tipos de acknowledgement"""
    VIEWED = "viewed"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    COMMENTED = "commented"
    ASSIGNED = "assigned"
    ESCALATED = "escalated"

class EventType(Enum):
    """Tipos de eventos del sistema"""
    ALERT_CREATED = "alert_created"
    ALERT_UPDATED = "alert_updated"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_RESOLVED = "alert_resolved"
    ALERT_ESCALATED = "alert_escalated"
    NOTIFICATION_SENT = "notification_sent"
    NOTIFICATION_FAILED = "notification_failed"
    THRESHOLD_BREACHED = "threshold_breached"
    CONDITION_MET = "condition_met"
    SCHEDULE_TRIGGERED = "schedule_triggered"

# ============================================
# MODELOS DE ALERTAS Y EVENTOS
# ============================================

@dataclass
class AlertEvent:
    """Evento del sistema de alertas"""
    
    id: str
    event_type: EventType
    alert_id: Optional[str] = None
    notification_id: Optional[str] = None
    source: AlertSource = AlertSource.SYSTEM
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte evento a diccionario"""
        return {
            'id': self.id,
            'event_type': self.event_type.value,
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'description': self.description,
            'metadata': self.metadata
        }

@dataclass
class AlertRule:
    """Regla para generación automática de alertas"""
    
    id: str
    name: str
    description: str
    category: AlertCategory
    severity: AlertSeverity
    
    # Condiciones
    condition_type: str  # threshold, expression, schedule, etc.
    condition_config: Dict[str, Any]
    
    # Acciones
    channels: List[NotificationChannel]
    escalation_config: Optional[Dict[str, Any]] = None
    
    # Frecuencia
    cooldown_minutes: int = 60  # Tiempo entre alertas similares
    max_alerts_per_day: int = 100
    
    # Estado
    is_active: bool = True
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Métricas
    total_triggers: int = 0
    last_triggered: Optional[datetime] = None
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def evaluate_condition(self, context: Dict[str, Any]) -> bool:
        """Evalúa si la condición se cumple"""
        
        if self.condition_type == 'threshold':
            return self._evaluate_threshold(context)
        elif self.condition_type == 'expression':
            return self._evaluate_expression(context)
        elif self.condition_type == 'schedule':
            return self._evaluate_schedule(context)
        elif self.condition_type == 'comparison':
            return self._evaluate_comparison(context)
        
        return False
    
    def _evaluate_threshold(self, context: Dict[str, Any]) -> bool:
        """Evalúa condición de umbral"""
        value = context.get('value', 0)
        threshold = self.condition_config.get('threshold', 0)
        operator = self.condition_config.get('operator', 'gt')
        
        if operator == 'gt':
            return value > threshold
        elif operator == 'lt':
            return value < threshold
        elif operator == 'gte':
            return value >= threshold
        elif operator == 'lte':
            return value <= threshold
        elif operator == 'eq':
            return value == threshold
        elif operator == 'neq':
            return value != threshold
        elif operator == 'between':
            min_val = self.condition_config.get('min', 0)
            max_val = self.condition_config.get('max', 0)
            return min_val <= value <= max_val
        elif operator == 'outside':
            min_val = self.condition_config.get('min', 0)
            max_val = self.condition_config.get('max', 0)
            return value < min_val or value > max_val
        
        return False
    
    def _evaluate_expression(self, context: Dict[str, Any]) -> bool:
        """Evalúa expresión personalizada"""
        expression = self.condition_config.get('expression', '')
        try:
            result = eval(expression, {"__builtins__": {}}, context)
            return bool(result)
        except:
            return False
    
    def _evaluate_schedule(self, context: Dict[str, Any]) -> bool:
        """Evalúa condición basada en horario"""
        current_time = context.get('current_time', datetime.now())
        schedule_type = self.condition_config.get('schedule_type', 'daily')
        
        if schedule_type == 'daily':
            start_time = self.condition_config.get('start_time', '09:00')
            end_time = self.condition_config.get('end_time', '18:00')
            current_str = current_time.strftime('%H:%M')
            return start_time <= current_str <= end_time
        
        return False
    
    def _evaluate_comparison(self, context: Dict[str, Any]) -> bool:
        """Evalúa comparación con período anterior"""
        current = context.get('current', 0)
        previous = context.get('previous', 0)
        operator = self.condition_config.get('operator', 'gt')
        percentage = self.condition_config.get('percentage', 10)
        
        change = ((current - previous) / abs(previous)) * 100 if previous != 0 else 0
        
        if operator == 'increase_gt':
            return change > percentage
        elif operator == 'decrease_gt':
            return change < -percentage
        elif operator == 'change_gt':
            return abs(change) > percentage
        
        return False
    
    def can_trigger(self) -> bool:
        """Verifica si se puede disparar la regla"""
        if not self.is_active:
            return False
        
        if self.total_triggers >= self.max_alerts_per_day:
            return False
        
        if self.last_triggered:
            cooldown_delta = timedelta(minutes=self.cooldown_minutes)
            if datetime.now() - self.last_triggered < cooldown_delta:
                return False
        
        return True
    
    def increment_trigger(self) -> None:
        """Incrementa contador de disparos"""
        self.total_triggers += 1
        self.last_triggered = datetime.now()
        self.updated_at = datetime.now()

@dataclass
class Alert:
    """Alerta del sistema"""
    
    id: str
    rule_id: Optional[str]
    title: str
    description: str
    category: AlertCategory
    severity: AlertSeverity
    source: AlertSource
    
    # Estado
    status: AlertStatus = AlertStatus.PENDING
    assigned_to: Optional[str] = None
    assigned_team: Optional[str] = None
    
    # Temporales
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Contexto
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Métricas
    value: Optional[float] = None
    threshold: Optional[float] = None
    unit: str = ""
    
    # Escalamiento
    escalation_level: EscalationLevel = EscalationLevel.LEVEL_1
    escalated_at: Optional[datetime] = None
    escalated_by: Optional[str] = None
    escalation_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Seguimiento
    acknowledgement_history: List[Dict[str, Any]] = field(default_factory=list)
    comments: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
        if not self.expires_at:
            self.expires_at = self.created_at + timedelta(days=7)
    
    def _generate_id(self) -> str:
        """Genera ID único para la alerta"""
        unique = f"{self.title}_{self.created_at.isoformat()}"
        return hashlib.md5(unique.encode()).hexdigest()[:20]
    
    def acknowledge(self, user_id: str, note: str = "") -> None:
        """Confirma la alerta"""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_at = datetime.now()
        self.updated_at = datetime.now()
        
        self.acknowledgement_history.append({
            'type': AcknowledgementType.ACKNOWLEDGED.value,
            'user_id': user_id,
            'timestamp': self.acknowledged_at.isoformat(),
            'note': note
        })
    
    def resolve(self, user_id: str, resolution: str, 
                resolution_notes: str = "") -> None:
        """Resuelve la alerta"""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now()
        self.updated_at = datetime.now()
        
        self.metadata['resolution'] = resolution
        self.metadata['resolution_notes'] = resolution_notes
        
        self.acknowledgement_history.append({
            'type': AcknowledgementType.RESOLVED.value,
            'user_id': user_id,
            'timestamp': self.resolved_at.isoformat(),
            'resolution': resolution,
            'notes': resolution_notes
        })
    
    def escalate(self, escalated_by: str, reason: str, 
                 to_level: EscalationLevel = None) -> None:
        """Escala la alerta a siguiente nivel"""
        previous_level = self.escalation_level
        
        if to_level:
            self.escalation_level = to_level
        else:
            next_level = self.escalation_level.value + 1
            if next_level <= EscalationLevel.LEVEL_5.value:
                self.escalation_level = EscalationLevel(next_level)
        
        self.status = AlertStatus.ESCALATED
        self.escalated_at = datetime.now()
        self.escalated_by = escalated_by
        self.updated_at = datetime.now()
        
        self.escalation_history.append({
            'from_level': previous_level.value,
            'to_level': self.escalation_level.value,
            'escalated_by': escalated_by,
            'timestamp': self.escalated_at.isoformat(),
            'reason': reason
        })
    
    def assign(self, assigned_to: str, assigned_by: str) -> None:
        """Asigna la alerta a un responsable"""
        self.assigned_to = assigned_to
        self.status = AlertStatus.IN_PROGRESS
        self.updated_at = datetime.now()
        
        self.acknowledgement_history.append({
            'type': AcknowledgementType.ASSIGNED.value,
            'user_id': assigned_by,
            'assigned_to': assigned_to,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_comment(self, user_id: str, comment: str) -> None:
        """Agrega comentario a la alerta"""
        self.comments.append({
            'user_id': user_id,
            'comment': comment,
            'timestamp': datetime.now().isoformat()
        })
        self.updated_at = datetime.now()
    
    def is_expired(self) -> bool:
        """Verifica si la alerta ha expirado"""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False
    
    def time_to_expiry(self) -> timedelta:
        """Tiempo restante para expiración"""
        if self.expires_at:
            return self.expires_at - datetime.now()
        return timedelta(0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte alerta a diccionario"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category.value,
            'severity': self.severity.value,
            'status': self.status.value,
            'assigned_to': self.assigned_to,
            'created_at': self.created_at.isoformat(),
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'value': self.value,
            'threshold': self.threshold,
            'escalation_level': self.escalation_level.value
        }

@dataclass
class Notification:
    """Notificación enviada"""
    
    id: str
    alert_id: str
    channel: NotificationChannel
    recipient: str
    subject: str
    content: str
    status: str = "pending"
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def mark_sent(self) -> None:
        self.status = "sent"
        self.sent_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_delivered(self) -> None:
        self.status = "delivered"
        self.delivered_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_read(self) -> None:
        self.status = "read"
        self.read_at = datetime.now()
        self.updated_at = datetime.now()
    
    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error_message = error
        self.retry_count += 1
        self.updated_at = datetime.now()

@dataclass
class ChannelConfig:
    """Configuración de canal de notificación"""
    
    channel: NotificationChannel
    is_active: bool = True
    priority: int = 5
    config: Dict[str, Any] = field(default_factory=dict)
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    rate_limit_per_day: int = 10000
    total_sent: int = 0
    total_failed: int = 0
    last_sent: Optional[datetime] = None

@dataclass
class EscalationPolicy:
    """Política de escalamiento"""
    
    id: str
    name: str
    description: str
    rules: List[Dict[str, Any]] = field(default_factory=list)
    initial_wait_minutes: int = 15
    escalation_wait_minutes: int = 30
    level_1_recipients: List[str] = field(default_factory=list)
    level_2_recipients: List[str] = field(default_factory=list)
    level_3_recipients: List[str] = field(default_factory=list)
    level_4_recipients: List[str] = field(default_factory=list)
    level_5_recipients: List[str] = field(default_factory=list)
    
    def get_recipients_for_level(self, level: EscalationLevel) -> List[str]:
        if level == EscalationLevel.LEVEL_1:
            return self.level_1_recipients
        elif level == EscalationLevel.LEVEL_2:
            return self.level_2_recipients
        elif level == EscalationLevel.LEVEL_3:
            return self.level_3_recipients
        elif level == EscalationLevel.LEVEL_4:
            return self.level_4_recipients
        elif level == EscalationLevel.LEVEL_5:
            return self.level_5_recipients
        return []
    
    def should_escalate(self, alert: Alert) -> bool:
        if alert.status not in [AlertStatus.PENDING, AlertStatus.ACKNOWLEDGED]:
            return False
        
        time_since_creation = datetime.now() - alert.created_at
        wait_time = self.initial_wait_minutes
        
        if alert.escalation_level != EscalationLevel.LEVEL_1:
            wait_time = self.escalation_wait_minutes * alert.escalation_level.value
        
        return time_since_creation > timedelta(minutes=wait_time)

class AlertEngine:
    """Motor principal de alertas y notificaciones"""
    
    def __init__(self):
        self.rules: Dict[str, AlertRule] = {}
        self.channels: Dict[NotificationChannel, ChannelConfig] = {}
        self.escalation_policies: Dict[str, EscalationPolicy] = {}
        
        # Estado
        self.alerts: Dict[str, Alert] = {}
        self.notifications: Dict[str, Notification] = {}
        self.events: List[AlertEvent] = []
        
        # Tracking
        self.alert_history: List[Dict[str, Any]] = []
        self.active_alerts_count = 0
        self.resolved_alerts_count = 0
        
        # Cooldown tracking
        self.rule_last_triggered: Dict[str, datetime] = {}
        
        # Inicializar canales por defecto
        self._init_default_channels()
        
        # Logger
        self.logger = logging.getLogger(__name__)
    
    def _init_default_channels(self) -> None:
        self.channels[NotificationChannel.EMAIL] = ChannelConfig(
            channel=NotificationChannel.EMAIL,
            priority=1,
            config={
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'use_tls': True,
                'from_email': 'alerts@empresa.com'
            }
        )
        self.channels[NotificationChannel.backend] = ChannelConfig(
            channel=NotificationChannel.backend,
            priority=2,
            config={
                'backendsocket_url': 'ws://localhost:8080/ws'
            }
        )
        self.channels[NotificationChannel.MOBILE] = ChannelConfig(
            channel=NotificationChannel.MOBILE,
            priority=3,
            config={
                'push_service': 'fcm',
                'api_key': 'your-api-key'
            }
        )
*** End Patch
