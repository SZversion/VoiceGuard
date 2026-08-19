from fastapi import APIRouter
from fastapi.exceptions import RequestValidationError

from app.api.exception_handlers import (
    request_validation_exception_handler,
    unhandled_exception_handler,
)
from app.api.main import app


app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

router = APIRouter()


@router.get("/api/test-error")
def test_error_route():
    raise RuntimeError("secret traceback")


app.include_router(router)
