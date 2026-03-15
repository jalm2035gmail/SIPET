from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from fastapi_modulo.db import MAIN
from fastapi_modulo.modulos.cartera_prestamos.modelos.enums import (
    BucketMora,
    EstadoCredito,
    EstadoPromesaPago,
    NivelRiesgo,
    ResultadoGestion,
    TipoGestionCobranza,
    TipoIndicador,
)


class CpCliente(MAIN):
    __tablename__ = "cp_cliente"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(40), nullable=False, unique=True, index=True)
    nombre_completo = Column(String(180), nullable=False)
    identificacion = Column(String(40), nullable=False, unique=True, index=True)
    telefono = Column(String(40), nullable=True)
    correo = Column(String(120), nullable=True)
    direccion = Column(String(255), nullable=True)
    segmento = Column(String(80), nullable=True)
    nivel_riesgo = Column(String(20), nullable=False, default=NivelRiesgo.BAJO.value)
    activo = Column(Boolean, nullable=False, default=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    creditos = relationship("CpCredito", back_populates="cliente", cascade="all, delete-orphan")


class CpCredito(MAIN):
    __tablename__ = "cp_credito"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("cp_cliente.id", ondelete="CASCADE"), nullable=False, index=True)
    numero_credito = Column(String(50), nullable=False, unique=True, index=True)
    producto = Column(String(100), nullable=False)
    fecha_desembolso = Column(Date, nullable=False, default=date.today)
    fecha_vencimiento = Column(Date, nullable=True)
    monto_original = Column(Numeric(14, 2), nullable=False, default=0)
    tasa_interes = Column(Numeric(8, 4), nullable=False, default=0)
    saldo_capital = Column(Numeric(14, 2), nullable=False, default=0)
    estado = Column(String(30), nullable=False, default=EstadoCredito.VIGENTE.value)
    bucket_mora = Column(String(20), nullable=False, default=BucketMora.CORRIENTE.value)
    dias_mora = Column(Integer, nullable=False, default=0)
    etapa_colocacion = Column(String(40), nullable=False, default="formalizacion")
    score_riesgo = Column(Numeric(7, 2), nullable=False, default=0)
    documentacion_completa = Column(Boolean, nullable=False, default=True)
    es_renovacion = Column(Boolean, nullable=False, default=False)
    oficial = Column(String(120), nullable=True)
    sucursal = Column(String(120), nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    cliente = relationship("CpCliente", back_populates="creditos")
    saldo = relationship("CpSaldoCredito", back_populates="credito", uselist=False, cascade="all, delete-orphan")
    mora = relationship("CpMoraCredito", back_populates="credito", uselist=False, cascade="all, delete-orphan")
    promesas_pago = relationship("CpPromesaPago", back_populates="credito", cascade="all, delete-orphan")
    gestiones = relationship("CpGestionCobranza", back_populates="credito", cascade="all, delete-orphan")
    castigos = relationship("CpCastigoCredito", back_populates="credito", cascade="all, delete-orphan")
    reestructuras = relationship("CpReestructuraCredito", back_populates="credito", cascade="all, delete-orphan")


class CpSaldoCredito(MAIN):
    __tablename__ = "cp_saldo_credito"
    __table_args__ = (UniqueConstraint("credito_id", name="uq_cp_saldo_credito_credito"),)

    id = Column(Integer, primary_key=True, index=True)
    credito_id = Column(Integer, ForeignKey("cp_credito.id", ondelete="CASCADE"), nullable=False, index=True)
    saldo_capital = Column(Numeric(14, 2), nullable=False, default=0)
    saldo_interes = Column(Numeric(14, 2), nullable=False, default=0)
    saldo_mora = Column(Numeric(14, 2), nullable=False, default=0)
    saldo_total = Column(Numeric(14, 2), nullable=False, default=0)
    fecha_corte = Column(Date, nullable=False, default=date.today)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    credito = relationship("CpCredito", back_populates="saldo")


class CpMoraCredito(MAIN):
    __tablename__ = "cp_mora_credito"
    __table_args__ = (UniqueConstraint("credito_id", name="uq_cp_mora_credito_credito"),)

    id = Column(Integer, primary_key=True, index=True)
    credito_id = Column(Integer, ForeignKey("cp_credito.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_exigible = Column(Date, nullable=True)
    dias_mora = Column(Integer, nullable=False, default=0)
    bucket = Column(String(20), nullable=False, default=BucketMora.CORRIENTE.value)
    monto_vencido = Column(Numeric(14, 2), nullable=False, default=0)
    porcentaje_cobertura = Column(Numeric(7, 4), nullable=False, default=0)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    credito = relationship("CpCredito", back_populates="mora")


class CpPromesaPago(MAIN):
    __tablename__ = "cp_promesa_pago"

    id = Column(Integer, primary_key=True, index=True)
    credito_id = Column(Integer, ForeignKey("cp_credito.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_promesa = Column(Date, nullable=False, default=date.today)
    fecha_compromiso = Column(Date, nullable=False)
    monto_comprometido = Column(Numeric(14, 2), nullable=False, default=0)
    monto_cumplido = Column(Numeric(14, 2), nullable=False, default=0)
    estado = Column(String(20), nullable=False, default=EstadoPromesaPago.PENDIENTE.value)
    observaciones = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)
    actualizado_en = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    credito = relationship("CpCredito", back_populates="promesas_pago")


class CpGestionCobranza(MAIN):
    __tablename__ = "cp_gestion_cobranza"

    id = Column(Integer, primary_key=True, index=True)
    credito_id = Column(Integer, ForeignKey("cp_credito.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_gestion = Column(DateTime, nullable=False, default=datetime.utcnow)
    tipo_gestion = Column(String(30), nullable=False, default=TipoGestionCobranza.LLAMADA.value)
    resultado = Column(String(30), nullable=False, default=ResultadoGestion.SIN_CONTACTO.value)
    responsable = Column(String(120), nullable=True)
    comentario = Column(Text, nullable=True)
    proxima_accion = Column(String(160), nullable=True)
    fecha_proxima_accion = Column(Date, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    credito = relationship("CpCredito", back_populates="gestiones")


class CpCastigoCredito(MAIN):
    __tablename__ = "cp_castigo_credito"

    id = Column(Integer, primary_key=True, index=True)
    credito_id = Column(Integer, ForeignKey("cp_credito.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_castigo = Column(Date, nullable=False, default=date.today)
    monto_castigado = Column(Numeric(14, 2), nullable=False, default=0)
    motivo = Column(String(180), nullable=True)
    aprobado_por = Column(String(120), nullable=True)
    observaciones = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    credito = relationship("CpCredito", back_populates="castigos")


class CpReestructuraCredito(MAIN):
    __tablename__ = "cp_reestructura_credito"

    id = Column(Integer, primary_key=True, index=True)
    credito_id = Column(Integer, ForeignKey("cp_credito.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_reestructura = Column(Date, nullable=False, default=date.today)
    nuevo_plazo_meses = Column(Integer, nullable=True)
    nueva_tasa = Column(Numeric(8, 4), nullable=True)
    cuota_anterior = Column(Numeric(14, 2), nullable=True)
    cuota_nueva = Column(Numeric(14, 2), nullable=True)
    justificacion = Column(Text, nullable=True)
    aprobado_por = Column(String(120), nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)

    credito = relationship("CpCredito", back_populates="reestructuras")


class CpIndicadorCartera(MAIN):
    __tablename__ = "cp_indicador_cartera"

    id = Column(Integer, primary_key=True, index=True)
    fecha_corte = Column(Date, nullable=False, default=date.today, index=True)
    tipo_indicador = Column(String(30), nullable=False, default=TipoIndicador.MORA.value, index=True)
    nombre = Column(String(120), nullable=False)
    valor = Column(Numeric(14, 4), nullable=False, default=0)
    meta = Column(Numeric(14, 4), nullable=True)
    semaforo = Column(String(20), nullable=False, default=NivelRiesgo.BAJO.value)
    detalle = Column(Text, nullable=True)
    creado_en = Column(DateTime, nullable=False, default=datetime.utcnow)


__all__ = [
    "CpCastigoCredito",
    "CpCliente",
    "CpCredito",
    "CpGestionCobranza",
    "CpIndicadorCartera",
    "CpMoraCredito",
    "CpPromesaPago",
    "CpReestructuraCredito",
    "CpSaldoCredito",
]
