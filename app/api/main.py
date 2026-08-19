import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import request_validation_exception_handler, unhandled_exception_handler
from app.api.request_id import RequestIdMiddleware
from app.api.routes.analyze import router as analyze_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.core.request_controls import DuplicateJobLock, IpHasher, RateLimiter
from app.jobs.cleanup import TempDataStore
from app.jobs.registry import JobRegistry


def _allowed_origins() -> list[str]:
    origins = ["http://localhost:3000"]
    nuxt_origin = os.getenv("NUXT_ORIGIN")
    if nuxt_origin and nuxt_origin not in origins:
        origins.append(nuxt_origin)
    return origins


def create_app() -> FastAPI:
    app = FastAPI(title="Voice Phishing Call Analysis API", version="0.1.0")
    app.state.job_registry = JobRegistry()
    app.state.analyzer = None
    app.state.temp_data_store = TempDataStore()
    app.state.ip_hasher = IpHasher(os.getenv("IP_HASH_SECRET", "development-only-secret"))
    app.state.job_lock = DuplicateJobLock()
    app.state.rate_limiter = RateLimiter(
        max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "10")),
        window_seconds=float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(analyze_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    return app


app = create_app()
