from .support import (
    UUID,
    _payload,
    _response,
    client,
    override_auth_dependency,
    patch,
    uuid4,
)

def test_new_chat_generates_and_returns_uuid4() -> None:
    with patch(
        "app.main.process_chat_request",
        side_effect=lambda request, context, provider, user_id, **kwargs: _response(context.session_id),
    ):
        response = client.post("/api/v1/generation/chat", json=_payload())

    assert response.status_code == 200
    session_id = UUID(response.json()["session_id"])
    assert session_id.version == 4
    assert response.json()["model_used"] is None
    assert response.json()["metadata"] == {}


def test_chat_boundary_forwards_resource_selector_without_exposing_internal_filters():
    source = uuid4()
    with patch('app.main.process_chat_request', return_value=_response(uuid4())) as process:
        response = client.post('/api/v1/generation/chat', json=_payload(resource_id=str(source)))
    assert response.status_code == 200
    assert process.call_args.args[0].resource_id == source
    assert process.call_args.args[0].knowledge_source_id is None

def test_existing_session_id_is_preserved_and_propagated() -> None:
    session_id = uuid4()
    captured = {}

    def process(request, context, provider, user_id, **kwargs):
        captured["session_id"] = context.session_id
        return _response(context.session_id)

    with patch("app.main.process_chat_request", side_effect=process):
        response = client.post(
            "/api/v1/generation/chat",
            json=_payload(session_id=str(session_id)),
        )

    assert response.status_code == 200
    assert response.json()["session_id"] == str(session_id)
    assert captured["session_id"] == session_id

def test_invalid_session_id_uses_fastapi_validation() -> None:
    with patch("app.main.process_chat_request") as process:
        response = client.post(
            "/api/v1/generation/chat",
            json=_payload(session_id="not-a-uuid"),
        )

    assert response.status_code == 422
    process.assert_not_called()

def test_chat_boundary_does_not_persist_records() -> None:
    with (
        patch(
            "app.main.process_chat_request",
            side_effect=lambda request, context, provider, user_id, **kwargs: _response(context.session_id),
        ),
        patch("app.db.supabase.get_admin_client") as get_admin_client,
    ):
        response = client.post("/api/v1/generation/chat", json=_payload())

    assert response.status_code == 200
    get_admin_client.assert_not_called()
