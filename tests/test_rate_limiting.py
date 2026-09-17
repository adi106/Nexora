import uuid

from fastapi.testclient import TestClient
from starlette.requests import Request

from backend.app.core.rate_limit import (
    RateLimiter,
    login_rate_limiter,
    registration_rate_limiter,
)
from backend.app.db.dependencies import get_db
from backend.app.main import app


def _make_request(client_host: str = "1.2.3.4") -> Request:
    scope = {
        "type": "http",
        "client": (client_host, 12345),
        "headers": [],
    }
    return Request(scope)


def test_rate_limiter_blocks_after_threshold():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    request = _make_request()

    for _ in range(3):
        limiter(request)

    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        limiter(request)

    assert exc_info.value.status_code == 429


def test_rate_limiter_tracks_clients_independently():
    limiter = RateLimiter(max_requests=1, window_seconds=60)

    limiter(_make_request("10.0.0.1"))

    # A different client IP should not be affected by the first client's usage.
    limiter(_make_request("10.0.0.2"))


def test_rate_limiter_resets_after_window_elapses(monkeypatch):
    limiter = RateLimiter(max_requests=1, window_seconds=10)
    request = _make_request()

    current_time = [1000.0]
    monkeypatch.setattr("time.monotonic", lambda: current_time[0])

    limiter(request)

    current_time[0] += 11

    limiter(request)  # should not raise; the window has elapsed


def test_login_endpoint_enforces_real_rate_limit(test_db):
    login_rate_limiter.reset()

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as real_client:
            responses = [
                real_client.post(
                    "/api/v1/auth/login",
                    data={"username": "nobody@nexora.com", "password": "wrong"},
                )
                for _ in range(login_rate_limiter.max_requests + 1)
            ]
    finally:
        app.dependency_overrides.clear()
        login_rate_limiter.reset()

    assert responses[-1].status_code == 429
    assert all(r.status_code == 401 for r in responses[:-1])


def test_registration_endpoint_enforces_real_rate_limit(test_db):
    registration_rate_limiter.reset()

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as real_client:
            responses = []
            for _ in range(registration_rate_limiter.max_requests + 1):
                responses.append(
                    real_client.post(
                        "/api/v1/users",
                        json={
                            "email": f"ratelimit.{uuid.uuid4().hex[:8]}@nexora.com",
                            "password": "TestPassword123!",
                            "first_name": "Rate",
                            "last_name": "Limited",
                        },
                    )
                )
    finally:
        app.dependency_overrides.clear()
        registration_rate_limiter.reset()

    assert responses[-1].status_code == 429
    assert all(r.status_code == 201 for r in responses[:-1])
