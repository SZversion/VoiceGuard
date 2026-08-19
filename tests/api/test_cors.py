from fastapi.testclient import TestClient

from app.api.main import app


def test_cors_allows_local_nuxt_origin():
    response = TestClient(app).get(
        "/api/health",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
