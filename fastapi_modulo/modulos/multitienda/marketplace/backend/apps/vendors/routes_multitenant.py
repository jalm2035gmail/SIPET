from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .utils import create_store_schema_and_migrate

router = APIRouter()

class StoreRegisterRequest(BaseModel):
    store_slug: str
    # otros campos como nombre, email, etc.

@router.post("/register-store/")
def register_store(data: StoreRegisterRequest):
    # Validar slug, etc.
    try:
        ok = create_store_schema_and_migrate(data.store_slug)
        if not ok:
            raise Exception("No se pudo crear el schema")
        # Aquí puedes guardar la tienda en la tabla global de tiendas, etc.
        return {"success": True, "message": f"Tienda '{data.store_slug}' creada y migrada"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
