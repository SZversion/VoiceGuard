from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.errors import error_response


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return error_response(
        request,
        "REQUEST.INVALID",
        "요청 형식이 올바르지 않습니다.",
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        request,
        "INTERNAL.ERROR",
        "서버 내부 오류가 발생했습니다.",
    )
