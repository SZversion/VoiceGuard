from fastapi import APIRouter, Request

from app.api.errors import error_response


router = APIRouter(tags=["jobs"])


def _job_or_error(request: Request, job_id: str):
    job = request.app.state.job_registry.get(job_id)
    if job is None:
        return None, error_response(request, "JOB.NOT_FOUND", "작업을 찾을 수 없습니다.")
    return job, None


@router.get("/analyze/{job_id}/status", summary="Get analysis job status")
def get_status(request: Request, job_id: str):
    job, error = _job_or_error(request, job_id)
    if error:
        return error
    return {"job_id": job.job_id, "status": job.status, "stage": job.stage}


@router.get("/analyze/{job_id}/result", summary="Get completed analysis result")
def get_result(request: Request, job_id: str):
    job, error = _job_or_error(request, job_id)
    if error:
        return error
    if job.status != "completed":
        return error_response(request, "JOB.NOT_COMPLETED", "작업이 아직 완료되지 않았습니다.")
    return {"job_id": job.job_id, "result": job.result}


@router.delete("/analyze/{job_id}", summary="Cancel analysis job")
def cancel_job(request: Request, job_id: str):
    job, error = _job_or_error(request, job_id)
    if error:
        return error
    if not request.app.state.job_registry.cancel(job_id):
        return error_response(request, "JOB.CANNOT_CANCEL", "완료되었거나 종료된 작업은 취소할 수 없습니다.")
    request.app.state.task_registry.cancel(job_id)
    return {"job_id": job.job_id, "status": job.status}
