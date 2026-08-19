import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router


def _allowed_origins() -> list[str]:
    origins = ["http://localhost:3000"]
    nuxt_origin = os.getenv("NUXT_ORIGIN")
    if nuxt_origin and nuxt_origin not in origins:
        origins.append(nuxt_origin)
    return origins


def create_app() -> FastAPI:
    app = FastAPI(
        title="Voice Phishing Call Analysis API",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api")
    return app


app = create_app()
