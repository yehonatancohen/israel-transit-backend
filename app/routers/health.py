from fastapi import APIRouter

router = APIRouter()

@router.get("/", summary="Liveness probe")
def health():
    return {"ok": True}
