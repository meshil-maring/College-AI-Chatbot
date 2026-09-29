"""Phase 7.8 public-chat abuse and resource-control tests."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core.errors import AppError
from app.main import app
from app.middleware.public_body_limit import PublicChatBodyLimitMiddleware
from app.schemas.chat import PublicChatResponse
from app.services.public_abuse_controls import (
    SlidingWindowRateLimiter,
    concurrency_gate,
    reset_public_abuse_state,
)


ENDPOINT = "/api/v1/chat/public"
PAYLOAD = {"institution_code": "COLLEGE-A", "message": "What programs are offered?"}


@pytest.fixture(autouse=True)
def _isolated_controls(monkeypatch):
    reset_public_abuse_state()
    monkeypatch.setattr(settings, "public_rate_limit_enabled", False)
    monkeypatch.setattr(settings, "public_concurrency_limit", 8)
    monkeypatch.setattr(settings, "public_institution_concurrency_limit", 4)
    yield
    reset_public_abuse_state()


def _success(*_args, **_kwargs) -> PublicChatResponse:
    return PublicChatResponse(answer="A safe answer.", status="success", sources=[])


def _post(payload=None, *, headers=None, client_address=("198.51.100.10", 50000)):
    with patch("app.main.process_public_request", side_effect=_success):
        return TestClient(app, client=client_address).post(
            ENDPOINT, json=payload or PAYLOAD, headers=headers
        )


def test_rate_limit_below_at_above_limit_and_window_reset():
    now = [100.0]
    limiter = SlidingWindowRateLimiter(clock=lambda: now[0])
    rules = [("client", "198.51.100.1", 2)]

    assert limiter.check(rules, 10) is None
    assert limiter.check(rules, 10) is None
    assert limiter.check(rules, 10) == 10
    now[0] = 110.0
    assert limiter.check(rules, 10) is None


def test_rate_limits_independent_clients_and_institutions(monkeypatch):
    monkeypatch.setattr(settings, "public_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "public_rate_limit_requests", 10)
    monkeypatch.setattr(settings, "public_institution_rate_limit_requests", 1)
    monkeypatch.setattr(settings, "public_global_rate_limit_requests", 10)

    assert _post().status_code == 200
    blocked = _post()
    assert blocked.status_code == 429
    assert blocked.json()["error"] == {
        "code": "PUBLIC_RATE_LIMITED",
        "message": "The public chatbot is busy. Please try again shortly.",
    }
    assert int(blocked.headers["retry-after"]) >= 1
    other_tenant = _post({**PAYLOAD, "institution_code": "COLLEGE-B"})
    assert other_tenant.status_code == 200

    reset_public_abuse_state()
    monkeypatch.setattr(settings, "public_rate_limit_requests", 1)
    monkeypatch.setattr(settings, "public_institution_rate_limit_requests", 10)
    assert _post(client_address=("198.51.100.1", 1)).status_code == 200
    assert _post(client_address=("198.51.100.2", 1)).status_code == 200


def test_spoofed_forwarding_header_cannot_bypass_peer_ip_limit(monkeypatch):
    monkeypatch.setattr(settings, "public_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "public_rate_limit_requests", 1)
    monkeypatch.setattr(settings, "public_institution_rate_limit_requests", 10)
    monkeypatch.setattr(settings, "public_global_rate_limit_requests", 10)

    assert _post(headers={"X-Forwarded-For": "198.51.100.1"}).status_code == 200
    response = _post(headers={"X-Forwarded-For": "203.0.113.99"})
    assert response.status_code == 429


def test_concurrency_available_limit_reached_and_release(monkeypatch):
    monkeypatch.setattr(settings, "public_concurrency_limit", 1)
    monkeypatch.setattr(settings, "public_institution_concurrency_limit", 1)
    held = concurrency_gate.try_acquire("COLLEGE-A")
    assert held is not None
    response = _post()
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PUBLIC_CHAT_BUSY"
    assert response.headers["retry-after"] == str(settings.public_overload_retry_after_seconds)
    held.release()
    assert _post().status_code == 200


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [
        (RuntimeError("SELECT secret FROM private_table"), 500),
        (
            AppError(
                "Public AI generation timed out. Please try again later.",
                status_code=504,
                code="PUBLIC_GENERATION_TIMEOUT",
            ),
            504,
        ),
    ],
)
def test_concurrency_slot_released_after_exception_or_timeout(
    monkeypatch, failure, expected_status
):
    monkeypatch.setattr(settings, "public_concurrency_limit", 1)
    monkeypatch.setattr(settings, "public_institution_concurrency_limit", 1)
    with patch("app.main.process_public_request", side_effect=[failure, _success()]):
        client = TestClient(app, raise_server_exceptions=False)
        first = client.post(ENDPOINT, json=PAYLOAD)
        second = client.post(ENDPOINT, json=PAYLOAD)
    assert first.status_code == expected_status
    assert "secret" not in first.text.lower()
    assert second.status_code == 200


@pytest.mark.parametrize(("length", "status"), [(3999, 200), (4000, 200), (4001, 422)])
def test_server_message_size_boundary(length, status):
    response = _post({"institution_code": "COLLEGE-A", "message": "x" * length})
    assert response.status_code == status


def test_public_http_body_is_rejected_before_service(monkeypatch):
    monkeypatch.setattr(settings, "public_max_body_bytes", 4096)
    with patch("app.main.process_public_request") as process:
        response = TestClient(app).post(
            ENDPOINT,
            content=b"{" + (b"x" * 4096) + b"}",
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PUBLIC_REQUEST_TOO_LARGE"
    process.assert_not_called()


@pytest.mark.asyncio
async def test_slow_public_body_receives_safe_408(monkeypatch):
    import asyncio

    monkeypatch.setattr(settings, "public_body_read_timeout_seconds", 0.001)

    async def downstream(_scope, _receive, _send):
        raise AssertionError("timed-out body reached application")

    async def slow_receive():
        await asyncio.sleep(1)
        return {"type": "http.request", "body": b"", "more_body": False}

    sent = []

    async def send(message):
        sent.append(message)

    middleware = PublicChatBodyLimitMiddleware(downstream)
    await middleware(
        {"type": "http", "method": "POST", "path": ENDPOINT, "headers": []},
        slow_receive,
        send,
    )
    assert sent[0]["status"] == 408
    assert b"PUBLIC_REQUEST_TIMEOUT" in sent[1]["body"]


def test_client_cannot_override_cost_or_provider_controls():
    for field in ("top_k", "max_tokens", "model", "provider", "temperature", "system_prompt"):
        response = _post({**PAYLOAD, field: 999})
        assert response.status_code == 422
    assert settings.retrieval_top_k <= 20
    assert settings.public_context_max_chunk_chars <= settings.public_context_max_chars
    assert settings.public_generation_max_tokens <= 4096
    assert settings.public_generation_timeout_seconds <= 30


def test_operational_logging_never_records_message(caplog):
    secret_message = "do-not-log-this-anonymous-message"
    with caplog.at_level(logging.INFO):
        response = _post({**PAYLOAD, "message": secret_message})
    assert response.status_code == 200
    assert secret_message not in caplog.text
    assert "event=public_chat_request" in caplog.text


def test_bounded_hundred_request_simulation_uses_no_real_provider(monkeypatch):
    monkeypatch.setattr(settings, "public_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "public_rate_limit_requests", 25)
    monkeypatch.setattr(settings, "public_institution_rate_limit_requests", 100)
    monkeypatch.setattr(settings, "public_global_rate_limit_requests", 100)
    with patch("app.main.process_public_request", side_effect=_success) as process:
        client = TestClient(app)
        statuses = [client.post(ENDPOINT, json=PAYLOAD).status_code for _ in range(100)]
    assert statuses.count(200) == 25
    assert statuses.count(429) == 75
    assert process.call_count == 25


def test_hundred_simulated_concurrent_admissions_are_globally_bounded(monkeypatch):
    monkeypatch.setattr(settings, "public_concurrency_limit", 8)
    monkeypatch.setattr(settings, "public_institution_concurrency_limit", 4)
    leases = [
        concurrency_gate.try_acquire(f"COLLEGE-{index % 10}")
        for index in range(100)
    ]
    admitted = [lease for lease in leases if lease is not None]
    assert len(admitted) == 8
    for lease in admitted:
        lease.release()
    assert concurrency_gate.try_acquire("COLLEGE-NEXT") is not None
