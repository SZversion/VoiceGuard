from fastapi import APIRouter, File, UploadFile

from app.analysis.audio import AudioValidationError, validate_audio
from app.api.errors import error_response


router = APIRouter(tags=["analysis"])


@router.post("/analyze", summary="Create an audio analysis job")
async def analyze(audio: UploadFile = File(...)):
    data = await audio.read()

    try:
        validate_audio(audio.filename, audio.content_type, data)
    except AudioValidationError as exc:
        return error_response(400, exc.error_code, "upload_validation", exc.message, False)

    return error_response(
        503,
        "MODEL.NOT_READY",
        "model_loading",
        "분석 모델이 아직 준비되지 않았습니다.",
        True,
    )
