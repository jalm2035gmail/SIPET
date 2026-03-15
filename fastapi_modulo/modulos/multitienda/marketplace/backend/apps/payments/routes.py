from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_payments():
    return ["payment1", "payment2"]
