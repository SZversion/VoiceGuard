from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.errors import ERROR_DEFINITIONS, error_response
from app.api.main import app
from app.api.schemas import ErrorResponse


def test_error_response_model_restricts_stage_values():
    with pytest.raises(ValidationError):
        ErrorResponse(
            request_id="req_test",
            error_code="REQUEST.INVALID",
            stage="unknown_stage",
            message="bad request",
            retryable=False,
        )


def test_error_code_mapping_contains_http_and_retry_metadata():
    definition = ERROR_DEFINITIONS["MODEL.NOT_READY"]

    assert definition.status_code == 503
    assert definition.stage == "model_loading"
    assert definition.retryable is True


def test_error_response_reuses_request_state_id():
    request = Mock()
    request.state.request_id = "req_shared"

    response = error_response(request, "MODEL.NOT_READY", "ignored message")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    assert b'"request_id":"req_shared"' in response.body


def test_internal_error_uses_fixed_message_and_request_id():
    response = TestClient(app, raise_server_exceptions=False).get("/api/test-error")

    assert response.status_code == 500
    body = response.json()
    assert body["request_id"].startswith("req_")
    assert body["message"] == "서버 내부 오류가 발생했습니다."
    assert body["stage"] == "server"
