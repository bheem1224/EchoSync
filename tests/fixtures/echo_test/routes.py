from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
def ping():
    return {"status": "v2"}
