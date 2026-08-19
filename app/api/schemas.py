from typing import Literal

from pydantic import BaseModel


ErrorStage = Literal[
    "request_validation",
    "upload_validation",
    "model_loading",
    "job_lookup",
    "job_cancel",
    "server",
]


class ErrorResponse(BaseModel):
    request_id: str
    error_code: str
    stage: ErrorStage
    message: str
    retryable: bool
