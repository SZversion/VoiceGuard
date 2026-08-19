from uuid import uuid4

from fastapi.responses import JSONResponse


def error_response(status_code: int, error_code: str, stage: str, message: str, retryable: bool) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": f"req_{uuid4().hex[:12]}",
            "error_code": error_code,
            "stage": stage,
            "message": message,
            "retryable": retryable,
        },
    )
