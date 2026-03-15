from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from fastapi_modulo.db import MAIN


class IntelicoopSocio(MAIN):
    __tablename__ = "intelicoop_socios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False, unique=True, index=True)
    telefono = Column(String(30), nullable=False, default="")
    direccion = Column(String(255), nullable=False, default="")
    segmento = Column(String(30), nullable=False, default="inactivo")
    fecha_registro = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntelicoopCredito(MAIN):
    __tablename__ = "intelicoop_creditos"

    id = Column(Integer, primary_key=True, index=True)
    socio_id = Column(Integer, ForeignKey("intelicoop_socios.id"), nullable=False, index=True)
    monto = Column(Float, nullable=False, default=0)
    plazo = Column(Integer, nullable=False, default=1)
    ingreso_mensual = Column(Float, nullable=False, default=0)
    deuda_actual = Column(Float, nullable=False, default=0)
    antiguedad_meses = Column(Integer, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="solicitado")
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntelicoopHistorialPago(MAIN):
    __tablename__ = "intelicoop_historial_pagos"

    id = Column(Integer, primary_key=True, index=True)
    credito_id = Column(Integer, ForeignKey("intelicoop_creditos.id"), nullable=False, index=True)
    monto = Column(Float, nullable=False, default=0)
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntelicoopCuenta(MAIN):
    __tablename__ = "intelicoop_cuentas"

    id = Column(Integer, primary_key=True, index=True)
    socio_id = Column(Integer, ForeignKey("intelicoop_socios.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False, default="ahorro")
    saldo = Column(Float, nullable=False, default=0)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntelicoopTransaccion(MAIN):
    __tablename__ = "intelicoop_transacciones"

    id = Column(Integer, primary_key=True, index=True)
    cuenta_id = Column(Integer, ForeignKey("intelicoop_cuentas.id"), nullable=False, index=True)
    monto = Column(Float, nullable=False, default=0)
    tipo = Column(String(20), nullable=False, default="deposito")
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntelicoopCampania(MAIN):
    __tablename__ = "intelicoop_campanas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    tipo = Column(String(100), nullable=False)
    fecha_inicio = Column(String(20), nullable=False, default="")
    fecha_fin = Column(String(20), nullable=False, default="")
    estado = Column(String(20), nullable=False, default="borrador")
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntelicoopProspecto(MAIN):
    __tablename__ = "intelicoop_prospectos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    telefono = Column(String(30), nullable=False, default="")
    direccion = Column(String(255), nullable=False, default="")
    fuente = Column(String(100), nullable=False, default="")
    score_propension = Column(Float, nullable=False, default=0)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntelicoopContactoCampania(MAIN):
    __tablename__ = "intelicoop_contactos_campania"

    id = Column(Integer, primary_key=True, index=True)
    campania_id = Column(Integer, ForeignKey("intelicoop_campanas.id"), nullable=False, index=True)
    socio_id = Column(Integer, ForeignKey("intelicoop_socios.id"), nullable=False, index=True)
    ejecutivo_id = Column(String(60), nullable=False, default="ejecutivo_general")
    canal = Column(String(30), nullable=False, default="telefono")
    estado_contacto = Column(String(20), nullable=False, default="pendiente")
    fecha_contacto = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntelicoopSeguimientoCampania(MAIN):
    __tablename__ = "intelicoop_seguimiento_campania"

    id = Column(Integer, primary_key=True, index=True)
    campania_id = Column(Integer, ForeignKey("intelicoop_campanas.id"), nullable=False, index=True)
    socio_id = Column(Integer, ForeignKey("intelicoop_socios.id"), nullable=False, index=True)
    lista = Column(String(30), nullable=False, default="general")
    etapa = Column(String(30), nullable=False, default="contactado")
    conversion = Column(Integer, nullable=False, default=0)
    monto_colocado = Column(Float, nullable=False, default=0)
    fecha_evento = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)


class IntelicoopScoringResult(MAIN):
    __tablename__ = "intelicoop_scoring_results"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(String(120), nullable=False, index=True)
    socio_id = Column(Integer, ForeignKey("intelicoop_socios.id"), nullable=True, index=True)
    credito_id = Column(Integer, ForeignKey("intelicoop_creditos.id"), nullable=True, index=True)
    ingreso_mensual = Column(Float, nullable=False, default=0)
    deuda_actual = Column(Float, nullable=False, default=0)
    antiguedad_meses = Column(Integer, nullable=False, default=0)
    score = Column(Float, nullable=False, default=0)
    recomendacion = Column(String(30), nullable=False, default="evaluar")
    riesgo = Column(String(10), nullable=False, default="medio")
    model_version = Column(String(60), nullable=False, default="intelicoop_scoring_v1")
    fecha_creacion = Column(DateTime, nullable=False, default=datetime.utcnow)
