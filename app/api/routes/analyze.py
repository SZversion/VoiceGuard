from fastapi import APIRouter, File, Request, UploadFile

from app.analysis.audio import AudioValidationError, validate_audio
from app.api.errors import error_response
from app.api.schemas import ErrorResponse


router = APIRouter(tags=["analysis"])


@router.post(
    "/analyze",
    summary="Create an audio analysis job",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid audio or request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
        503: {"model": ErrorResponse, "description": "Analysis model is not ready"},
    },
)
async def analyze(request: Request, audio: UploadFile = File(...)):
    data = await audio.read()
    try:
        validate_audio(audio.filename, audio.content_type, data)
    except AudioValidationError as exc:
        return error_response(request, exc.error_code, exc.message)
    return error_response(request, "MODEL.NOT_READY", "분석 모델이 아직 준비되지 않았습니다.")
