from pathlib import Path


ROOT = Path(__file__).parents[2]


def test_dockerfile_runs_fastapi_on_railway_port():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "app.api.main:app" in dockerfile
    assert "0.0.0.0" in dockerfile
    assert "$PORT" in dockerfile or "${PORT" in dockerfile


def test_env_example_documents_backend_runtime_variables():
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "IP_HASH_SECRET=" in env_example
    assert "RATE_LIMIT_MAX_REQUESTS=" in env_example
    assert "RATE_LIMIT_WINDOW_SECONDS=" in env_example
    assert "NUXT_ORIGIN=" in env_example
