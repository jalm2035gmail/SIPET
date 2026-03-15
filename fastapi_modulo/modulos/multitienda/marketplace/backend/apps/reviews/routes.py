from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_reviews():
    return ["review1", "review2"]
