from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.schemas import ErrorResponse


@dataclass(frozen=True)
class ErrorDefinition:
    status_code: int
    stage: str
    retryable: bool


ERROR_DEFINITIONS = {
    "REQUEST.INVALID": ErrorDefinition(400, "request_validation", False),
    "AUDIO.UNSUPPORTED_FORMAT": ErrorDefinition(400, "upload_validation", False),
    "AUDIO.EMPTY": ErrorDefinition(400, "upload_validation", False),
    "AUDIO.INVALID_FORMAT": ErrorDefinition(400, "upload_validation", False),
    "MODEL.NOT_READY": ErrorDefinition(503, "model_loading", True),
    "INTERNAL.ERROR": ErrorDefinition(500, "server", True),
}


def error_response(request: Request, error_code: str, message: str) -> JSONResponse:
    definition = ERROR_DEFINITIONS[error_code]
    payload = ErrorResponse(
        request_id=request.state.request_id,
        error_code=error_code,
        stage=definition.stage,
        message=message,
        retryable=definition.retryable,
    )
    return JSONResponse(status_code=definition.status_code, content=payload.model_dump())
