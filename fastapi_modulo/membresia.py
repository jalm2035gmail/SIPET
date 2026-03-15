from html import escape

from sqlalchemy import Column, Float, Integer, String, Text, inspect, text
from fastapi_modulo.db import MAIN, SessionLocal, engine
from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

membresia_router = APIRouter()
templates = Jinja2Templates(directory=["fastapi_modulo/templates", "fastapi_modulo"])


def _get_colores_context() -> dict:
    from fastapi_modulo.main import get_colores_context
    return get_colores_context()


class Membresia(MAIN):
    __tablename__ = "membresias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False)
    descripcion = Column(Text, nullable=True)
    caracteristicas = Column(Text, nullable=True)
    tipo = Column(String(50), nullable=False)
    apps_disponibles = Column(Text, nullable=True)
    precio_por_usuario = Column(Float, nullable=True)
    minimo_usuarios = Column(Integer, nullable=True)
    maximo_usuarios = Column(Integer, nullable=True)
    plan_mensual = Column(Float, nullable=True)
    plan_anual = Column(Float, nullable=True)

    def __repr__(self):
        return f"<Membresia(nombre={self.nombre}, tipo={self.tipo})>"


def _ensure_membresia_table() -> None:
    Membresia.__table__.create(bind=engine, checkfirst=True)
    inspector = inspect(engine)
    columnas = {col["name"] for col in inspector.get_columns(Membresia.__tablename__)}
    alter_statements = []
    if "apps_disponibles" not in columnas:
        alter_statements.append('ALTER TABLE membresias ADD COLUMN apps_disponibles TEXT')
    if "precio_por_usuario" not in columnas:
        alter_statements.append('ALTER TABLE membresias ADD COLUMN precio_por_usuario FLOAT')
    if "minimo_usuarios" not in columnas:
        alter_statements.append('ALTER TABLE membresias ADD COLUMN minimo_usuarios INTEGER')
    if "maximo_usuarios" not in columnas:
        alter_statements.append('ALTER TABLE membresias ADD COLUMN maximo_usuarios INTEGER')
    if "plan_mensual" not in columnas:
        alter_statements.append('ALTER TABLE membresias ADD COLUMN plan_mensual FLOAT')
    if "plan_anual" not in columnas:
        alter_statements.append('ALTER TABLE membresias ADD COLUMN plan_anual FLOAT')

    if alter_statements:
        with engine.begin() as conn:
            for statement in alter_statements:
                conn.execute(text(statement))


MEMBRESIAS_PREDETERMINADAS = [
    {
        "nombre": "Básica",
        "tipo": "Básica",
        "descripcion": "Plan inicial para equipos pequeños.",
        "caracteristicas": "Acceso esencial a la plataforma.",
        "apps_disponibles": "Panel principal",
        "precio_por_usuario": 99.0,
        "minimo_usuarios": 1,
        "maximo_usuarios": 5,
        "plan_mensual": 99.0,
        "plan_anual": 999.0,
    },
    {
        "nombre": "Estándar",
        "tipo": "Estándar",
        "descripcion": "Plan para operación regular.",
        "caracteristicas": "Más módulos y cobertura operativa.",
        "apps_disponibles": "Panel principal, reportes, notificaciones",
        "precio_por_usuario": 149.0,
        "minimo_usuarios": 5,
        "maximo_usuarios": 25,
        "plan_mensual": 149.0,
        "plan_anual": 1499.0,
    },
    {
        "nombre": "Pro",
        "tipo": "Pro",
        "descripcion": "Plan avanzado para equipos con mayor demanda.",
        "caracteristicas": "Automatización y analítica ampliada.",
        "apps_disponibles": "Panel principal, reportes, notificaciones, IA",
        "precio_por_usuario": 229.0,
        "minimo_usuarios": 10,
        "maximo_usuarios": 100,
        "plan_mensual": 229.0,
        "plan_anual": 2299.0,
    },
    {
        "nombre": "Empresa",
        "tipo": "Empresa",
        "descripcion": "Plan corporativo con alcance extendido.",
        "caracteristicas": "Cobertura completa y escalabilidad.",
        "apps_disponibles": "Todas las apps disponibles",
        "precio_por_usuario": 349.0,
        "minimo_usuarios": 25,
        "maximo_usuarios": 1000,
        "plan_mensual": 349.0,
        "plan_anual": 3499.0,
    },
]


def _seed_membresias(db) -> None:
    existentes = {
        (membresia.nombre or "").strip().lower(): membresia
        for membresia in db.query(Membresia).all()
    }
    cambios = False
    for plan in MEMBRESIAS_PREDETERMINADAS:
        clave = plan["nombre"].strip().lower()
        membresia = existentes.get(clave)
        if membresia is None:
            db.add(Membresia(**plan))
            cambios = True
            continue

        for campo, valor in plan.items():
            actual = getattr(membresia, campo, None)
            if actual in (None, ""):
                setattr(membresia, campo, valor)
                cambios = True

    if cambios:
        db.commit()


def _render_MAIN(request: Request, title: str, description: str, content: str):
    return templates.TemplateResponse(
        "MAIN.html",
        {
            "request": request,
            "title": title,
            "description": description,
            "page_title": title,
            "page_description": description,
            "section_label": "",
            "section_title": "",
            "content": content,
            "floating_actions_html": "",
            "floating_actions_screen": "personalization",
            "hide_floating_actions": True,
            "show_page_header": True,
            "colores": _get_colores_context(),
        },
    )


@membresia_router.get("/membresia")
def listar_membresias(request: Request):
    _ensure_membresia_table()
    db = SessionLocal()
    try:
        _seed_membresias(db)
        membresias = db.query(Membresia).order_by(Membresia.id.asc()).all()
    finally:
        db.close()

    membresia_contratada = membresias[0] if membresias else None
    resumen_membresia = {
        "membresia_contratada": membresia_contratada.nombre if membresia_contratada else "Sin membresía",
        "maximo_usuarios": int(membresia_contratada.maximo_usuarios or 0) if membresia_contratada else 0,
        "historico_pagos": "Sin registros",
        "pagos_pendientes": "0",
        "fecha_proximo_pago": "No programado",
    }

    rows_html = "".join(
        [
            (
                "<tr>"
                f"<td>{escape(membresia.nombre or '')}</td>"
                f"<td>{escape(membresia.apps_disponibles or '')}</td>"
                f"<td>${float(membresia.precio_por_usuario or 0):,.2f}</td>"
                f"<td>{int(membresia.minimo_usuarios or 0)}</td>"
                f"<td>{int(membresia.maximo_usuarios or 0)}</td>"
                f"<td>${float(membresia.plan_mensual or 0):,.2f}</td>"
                f"<td>${float(membresia.plan_anual or 0):,.2f}</td>"
                "</tr>"
            )
            for membresia in membresias
        ]
    )
    content = f"""
<section class="form-section">
    <div class="section-title">
        <h2>Resumen de Membresía</h2>
    </div>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:18px;">
        <article style="border:1px solid #dbe3ef;border-radius:12px;padding:14px;background:#fff;">
            <strong>Membresía contratada</strong>
            <div style="margin-top:6px;">{escape(str(resumen_membresia["membresia_contratada"]))}</div>
        </article>
        <article style="border:1px solid #dbe3ef;border-radius:12px;padding:14px;background:#fff;">
            <strong>Máximo de usuarios</strong>
            <div style="margin-top:6px;">{escape(str(resumen_membresia["maximo_usuarios"]))}</div>
        </article>
        <article style="border:1px solid #dbe3ef;border-radius:12px;padding:14px;background:#fff;">
            <strong>Histórico de pagos</strong>
            <div style="margin-top:6px;">{escape(str(resumen_membresia["historico_pagos"]))}</div>
        </article>
        <article style="border:1px solid #dbe3ef;border-radius:12px;padding:14px;background:#fff;">
            <strong>Pagos pendientes</strong>
            <div style="margin-top:6px;">{escape(str(resumen_membresia["pagos_pendientes"]))}</div>
        </article>
        <article style="border:1px solid #dbe3ef;border-radius:12px;padding:14px;background:#fff;">
            <strong>Fecha de próximo pago</strong>
            <div style="margin-top:6px;">{escape(str(resumen_membresia["fecha_proximo_pago"]))}</div>
        </article>
    </div>
</section>
<section class="form-section">
    <div class="section-title">
        <h2>Tipos de Membresía</h2>
    </div>
    <table>
        <thead>
            <tr>
                <th>Tipo de membresía</th>
                <th>Apps disponibles</th>
                <th>Precio por usuario</th>
                <th>Mínimo de usuarios</th>
                <th>Máximo de usuarios</th>
                <th>Plan mensual</th>
                <th>Plan anual</th>
            </tr>
        </thead>
        <tbody>
            {rows_html if rows_html else '<tr><td colspan="7">Sin membresías registradas.</td></tr>'}
        </tbody>
    </table>
</section>
"""
    return _render_MAIN(request, "Membresías", "Administra tipos de membresía y sus límites.", content)


@membresia_router.get("/membresia/nueva")
def nueva_membresia(request: Request):
    content = """
<section class="form-section">
    <div class="section-title">
        <h2>Nueva Membresía</h2>
    </div>
    <form method="post" action="/membresia/nueva" class="usuarios-form-layout">
        <div class="section-grid">
            <label class="form-field">
                <span>Nombre</span>
                <input type="text" id="nombre" name="nombre" required class="campo-personalizado">
            </label>
            <label class="form-field">
                <span>Tipo</span>
                <input type="text" id="tipo" name="tipo" required class="campo-personalizado">
            </label>
            <label class="form-field">
                <span>Apps disponibles</span>
                <textarea id="apps_disponibles" name="apps_disponibles" class="campo-personalizado"></textarea>
            </label>
            <label class="form-field">
                <span>Precio por usuario</span>
                <input type="number" step="0.01" min="0" id="precio_por_usuario" name="precio_por_usuario" class="campo-personalizado">
            </label>
            <label class="form-field">
                <span>Mínimo de usuarios</span>
                <input type="number" min="1" id="minimo_usuarios" name="minimo_usuarios" class="campo-personalizado">
            </label>
            <label class="form-field">
                <span>Máximo de usuarios</span>
                <input type="number" min="1" id="maximo_usuarios" name="maximo_usuarios" class="campo-personalizado">
            </label>
            <label class="form-field">
                <span>Plan mensual</span>
                <input type="number" step="0.01" min="0" id="plan_mensual" name="plan_mensual" class="campo-personalizado">
            </label>
            <label class="form-field">
                <span>Plan anual</span>
                <input type="number" step="0.01" min="0" id="plan_anual" name="plan_anual" class="campo-personalizado">
            </label>
            <label class="form-field">
                <span>Características</span>
                <textarea id="caracteristicas" name="caracteristicas" class="campo-personalizado"></textarea>
            </label>
            <label class="form-field">
                <span>Descripción</span>
                <textarea id="descripcion" name="descripcion" class="campo-personalizado"></textarea>
            </label>
        </div>
        <div class="color-actions">
            <button type="submit" class="color-btn color-btn--primary">Guardar</button>
            <a href="/membresia" class="color-btn color-btn--ghost">Cancelar</a>
        </div>
    </form>
</section>
"""
    return _render_MAIN(request, "Nueva Membresía", "Registrar una nueva membresía.", content)


@membresia_router.post("/membresia/nueva")
def crear_membresia(
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form(...),
    apps_disponibles: str = Form(None),
    precio_por_usuario: float = Form(None),
    minimo_usuarios: int = Form(None),
    maximo_usuarios: int = Form(None),
    plan_mensual: float = Form(None),
    plan_anual: float = Form(None),
    caracteristicas: str = Form(None),
    descripcion: str = Form(None),
):
    del request
    _ensure_membresia_table()
    db = SessionLocal()
    try:
        membresia = Membresia(
            nombre=(nombre or "").strip(),
            tipo=(tipo or "").strip(),
            apps_disponibles=(apps_disponibles or "").strip(),
            precio_por_usuario=precio_por_usuario,
            minimo_usuarios=minimo_usuarios,
            maximo_usuarios=maximo_usuarios,
            plan_mensual=plan_mensual,
            plan_anual=plan_anual,
            caracteristicas=(caracteristicas or "").strip(),
            descripcion=(descripcion or "").strip(),
        )
        db.add(membresia)
        db.commit()
    finally:
        db.close()
    return RedirectResponse(url="/membresia", status_code=303)
