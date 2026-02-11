from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api_router import api_router
from app.database import engine, Base

# Crear tablas
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Sistema de Planificación Estratégica")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Sistema de Planificación Estratégica y POA"}
