import logging
import os
import re
from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.analysis.analyzer import VoicePhishingAnalyzer
from app.analysis.domain_corrector import DomainTermCorrector, load_default_domain_rules
from app.analysis.model_loader import load_text_classifier
from app.analysis.whisper_lora_loader import load_whisper_lora_transcriber
from app.api.exception_handlers import request_validation_exception_handler, unhandled_exception_handler
from app.api.request_id import RequestIdMiddleware
from app.api.routes.analyze import router as analyze_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.core.request_controls import DuplicateJobLock, IpHasher, RateLimiter
from app.jobs.cleanup import TempDataStore
from app.jobs.registry import JobRegistry
from app.jobs.task_registry import JobTaskRegistry


logger = logging.getLogger(__name__)


def _redact_loader_error(message: str) -> str:
    redacted = re.sub(r"\bhf_[A-Za-z0-9_-]+\b", "[REDACTED]", message)
    for token_name in ("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        token = os.getenv(token_name)
        if token:
            redacted = redacted.replace(token, "[REDACTED]")
    return redacted


def _allowed_origins() -> list[str]:
    origins = ["http://localhost:3000"]
    nuxt_origin = os.getenv("NUXT_ORIGIN")
    if nuxt_origin and nuxt_origin not in origins:
        origins.append(nuxt_origin)
    return origins


def _initial_model_status() -> dict[str, str | bool]:
    return {
        "stt": "not_ready",
        "classifier": "not_ready",
        "analyzable": False,
    }


def _load_component(
    app: FastAPI,
    state_name: str,
    status_name: str,
    loader: Callable[[], object],
) -> None:
    try:
        setattr(app.state, state_name, loader())
    except Exception as exc:
        logger.error(
            "Model component load failed: %s (%s): %s",
            status_name,
            type(exc).__name__,
            _redact_loader_error(str(exc)),
        )
        setattr(app.state, state_name, None)
        app.state.model_status[status_name] = "error"
        return

    app.state.model_status[status_name] = "ready"


def _initialize_runtime(
    app: FastAPI,
    stt_loader: Callable[[], object],
    classifier_loader: Callable[[], object],
) -> None:
    _load_component(app, "transcriber", "stt", stt_loader)
    _load_component(app, "classifier", "classifier", classifier_loader)

    if (
        app.state.model_status["stt"] == "ready"
        and app.state.model_status["classifier"] == "ready"
    ):
        app.state.analyzer = VoicePhishingAnalyzer(
            app.state.transcriber,
            app.state.classifier,
            corrector=DomainTermCorrector(
                load_default_domain_rules(
                    Path(__file__).resolve().parents[2]
                    / "data"
                    / "stt_dictionary"
                    / "domain_corrections.json"
                )
            ),
        )
        app.state.model_status["analyzable"] = True


def create_app(
    stt_loader: Callable[[], object] | None = None,
    classifier_loader: Callable[[], object] | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _initialize_runtime(
            app,
            stt_loader or load_whisper_lora_transcriber,
            classifier_loader or load_text_classifier,
        )
        app.state.runtime_started = True
        try:
            yield
        finally:
            app.state.runtime_started = False

    app = FastAPI(
        title="Voice Phishing Call Analysis API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.job_registry = JobRegistry()
    app.state.analyzer = None
    app.state.transcriber = None
    app.state.classifier = None
    app.state.model_status = _initial_model_status()
    app.state.runtime_started = False
    app.state.temp_data_store = TempDataStore()
    app.state.ip_hasher = IpHasher(os.getenv("IP_HASH_SECRET", "development-only-secret"))
    app.state.job_lock = DuplicateJobLock()
    app.state.rate_limiter = RateLimiter(
        max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "10")),
        window_seconds=float(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
    )
    app.state.task_registry = JobTaskRegistry()
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
