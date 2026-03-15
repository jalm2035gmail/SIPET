from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.initial_data import seed_superadmin_role_and_user
from app.dataMAIN import engine, MAIN
from app.security.auth import security_middleware

# Crear tablas
MAIN.metadata.create_all(bind=engine)
seed_superadmin_role_and_user()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Integrar middleware de seguridad
app.middleware("http")(security_middleware)

# Incluir rutas
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {"message": f"{settings.PROJECT_NAME} API"}
