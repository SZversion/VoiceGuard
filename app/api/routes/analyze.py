import asyncio

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from app.analysis.audio import AudioValidationError, validate_audio
from app.api.errors import error_response
from app.api.schemas import ErrorResponse
from app.jobs.runner import JobRunner


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
async def create_analysis_job(request: Request, audio: UploadFile = File(...)):
    data = await audio.read()
    try:
        validate_audio(audio.filename, audio.content_type, data)
    except AudioValidationError as exc:
        return error_response(request, exc.error_code, exc.message)

    analyzer = request.app.state.analyzer
    if analyzer is None:
        return error_response(request, "MODEL.NOT_READY", "분석 모델이 아직 준비되지 않았습니다.")

    temp_path = request.app.state.temp_data_store.create(data)
    job = request.app.state.job_registry.create(owner_key=request.state.request_id)
    asyncio.create_task(
        JobRunner(request.app.state.job_registry, analyzer, request.app.state.temp_data_store).run(
            job.job_id,
            data,
            temp_path,
        )
    )
    return JSONResponse(status_code=202, content={"job_id": job.job_id, "status": "queued"})
