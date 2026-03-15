from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_orders():
    return ["order1", "order2"]
