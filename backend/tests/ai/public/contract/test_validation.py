from .support import (
    DOC_A,
    KS_A,
    PublicChatResponse,
    RUN_A,
    TestClient,
    VERSION_A,
    app,
    patch,
    pytest,
)

@pytest.mark.parametrize(
    "payload",
    [
        {"institution_code": "COLLEGE001", "message": ""},
        {"institution_code": "COLLEGE001", "message": "   \n\t"},
        {"institution_code": "COLLEGE001", "message": "x" * 4001},
        {"institution_code": "COLLEGE001"},
        {"message": "Hello"},
        {"institution_code": "", "message": "Hello"},
        {"institution_code": "COLLEGE001", "message": "Hello", "unknown": 1},
        {"institution_code": "COLLEGE001", "message": "Hello", "knowledge_source_id": KS_A},
        {"institution_code": "COLLEGE001", "message": "Hello", "document_id": DOC_A},
        {"institution_code": "COLLEGE001", "message": "Hello", "document_version_id": VERSION_A},
        {"institution_code": "COLLEGE001", "message": "Hello", "processing_run_id": RUN_A},
        {"institution_code": "COLLEGE001", "message": "Hello", "chunk_limit": 100},
        {"institution_code": "COLLEGE001", "message": "Hello", "similarity_threshold": 0},
        {"institution_code": "COLLEGE001", "message": "Hello", "embedding_model": "attacker"},
        {"institution_code": "COLLEGE001", "message": "Hello", "model": "attacker/model"},
        {"institution_code": "COLLEGE001", "message": "Hello", "temperature": 2},
        {"institution_code": "COLLEGE001", "message": "Hello", "token_limit": 999999},
        {"institution_code": "COLLEGE001", "message": "Hello", "provider": "attacker"},
        {"institution_code": "COLLEGE001", "message": "Hello", "debug": True},
    ],
)
def test_strict_request_validation_rejects_invalid_or_internal_input(payload):
    with patch("app.main.process_public_request") as process:
        response = TestClient(app).post("/api/v1/chat/public", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    process.assert_not_called()

def test_malformed_json_is_rejected_before_public_service():
    with patch("app.main.process_public_request") as process:
        response = TestClient(app).post(
            "/api/v1/chat/public",
            content=b'{"institution_code": "COLLEGE001",',
            headers={"content-type": "application/json"},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    process.assert_not_called()

def test_valid_request_needs_no_credentials_and_normalizes_input():
    captured = {}

    def process(request, _context, _provider):
        captured["request"] = request
        return PublicChatResponse(answer=None, status="insufficient_context")

    with patch("app.main.process_public_request", side_effect=process):
        response = TestClient(app).post(
            "/api/v1/chat/public",
            json={"institution_code": " college001 ", "message": "  What   courses? "},
        )
    assert response.status_code == 200
    assert captured["request"].institution_code == "COLLEGE001"
    assert captured["request"].message == "What courses?"
