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
        409: {"model": ErrorResponse, "description": "Duplicate active job"},
        429: {"model": ErrorResponse, "description": "Request rate limit exceeded"},
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

    client_ip = request.client.host if request.client else "unknown"
    owner_key = request.app.state.ip_hasher.hash_ip(client_ip)
    if not request.app.state.rate_limiter.allow(owner_key):
        return error_response(request, "SERVICE.RATE_LIMITED", "요청 제한을 초과했습니다.")

    analyzer = request.app.state.analyzer
    if analyzer is None:
        return error_response(request, "MODEL.NOT_READY", "분석 모델이 아직 준비되지 않았습니다.")
    if request.app.state.job_lock.is_locked(owner_key):
        return error_response(request, "JOB.DUPLICATE", "이미 진행 중인 작업이 있습니다.")

    temp_path = request.app.state.temp_data_store.create(data)
    job = request.app.state.job_registry.create(owner_key=owner_key)
    request.app.state.job_lock.acquire(owner_key, job.job_id)
    asyncio.create_task(
        JobRunner(
            request.app.state.job_registry,
            analyzer,
            request.app.state.temp_data_store,
            request.app.state.job_lock,
            owner_key,
        ).run(job.job_id, data, temp_path)
    )
    return JSONResponse(status_code=202, content={"job_id": job.job_id, "status": "queued"})
