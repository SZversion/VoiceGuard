from fastapi import APIRouter, Request


router = APIRouter(tags=["system"])


@router.get("/health", summary="Check API server health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/model-status", summary="Check analysis model status")
def model_status(request: Request) -> dict[str, str | bool]:
    if not getattr(request.app.state, "runtime_started", False):
        return {
            "stt": "not_ready",
            "classifier": "not_ready",
            "analyzable": False,
        }
    return dict(request.app.state.model_status)
