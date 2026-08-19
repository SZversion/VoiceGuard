from fastapi import APIRouter


router = APIRouter(tags=["system"])


@router.get("/health", summary="Check API server health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/model-status", summary="Check analysis model status")
def model_status() -> dict[str, str | bool]:
    return {
        "stt": "not_ready",
        "classifier": "not_ready",
        "analyzable": False,
    }
