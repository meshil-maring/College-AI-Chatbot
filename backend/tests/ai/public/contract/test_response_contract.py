from .support import (
    PublicChatResponse,
    app,
    pytest,
)

def test_openapi_documents_narrow_unauthenticated_contract():
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/chat/public"]["post"]
    request_ref = operation["requestBody"]["content"]["application/json"]["schema"]["$ref"]
    response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert request_ref.endswith("/PublicChatRequest")
    assert response_ref.endswith("/PublicChatResponse")
    assert not operation.get("security")
    assert "Authentication: Not required" in operation["description"]
    assert {"401", "403", "404", "422", "500"}.issubset(operation["responses"])

    request_schema = schema["components"]["schemas"]["PublicChatRequest"]
    assert request_schema["additionalProperties"] is False
    assert set(request_schema["properties"]) == {"institution_code", "message"}
    forbidden = {
        "knowledge_source_id",
        "document_id",
        "document_version_id",
        "processing_run_id",
        "model",
        "provider",
        "temperature",
        "token_limit",
        "debug",
    }
    assert forbidden.isdisjoint(request_schema["properties"])

def test_public_response_model_rejects_internal_metadata():
    with pytest.raises(Exception):
        PublicChatResponse(
            answer="Safe",
            status="success",
            sources=[],
            model_used="internal-model",
        )
