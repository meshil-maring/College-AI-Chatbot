from .fakes import (
    CHUNK_A,
    CHUNK_B,
    CHUNK_PRIVATE_A,
    DOC_A,
    DOC_B,
    ExitStack,
    GenerationResult,
    INST_A,
    INST_B,
    KS_A,
    KS_B,
    KS_PRIVATE_A,
    ORG_A,
    Path,
    PublicKnowledgePolicy,
    RUN_A,
    RUN_B,
    RUN_PRIVATE_A,
    RetrievedChunk,
    SimpleNamespace,
    TestClient,
    UUID,
    VERSION_A,
    VERSION_B,
    _Client,
    _Query,
    _RPC,
    _bound_public_context,
    _run,
    _source,
    app,
    deepcopy,
    patch,
    pytest,
    settings,
)

class _CapturingProvider:
    def __init__(self):
        self.contexts = []

    def generate(self, context):
        self.contexts.append(context)
        return GenerationResult(
            answer=f"Engineering is offered. [Retrieved chunk {CHUNK_A}]",
            model_used="test/internal",
            metadata={"usage": {"prompt_tokens": 9}},
        )

def _post(client: _Client, provider: _CapturingProvider, message: str = "Programs?"):
    with (
        patch("app.services.ai.public_chat.get_admin_client", return_value=client),
        patch("app.services.knowledge.retrieval.get_admin_client", return_value=client),
        patch("app.services.knowledge.retrieval.embed_query", return_value=[0.25] * 1536) as embed,
        patch("app.main.OpenRouterGenerationProvider", return_value=provider),
    ):
        response = TestClient(app, raise_server_exceptions=False).post(
            "/api/v1/chat/public",
            json={"institution_code": "college-a", "message": message},
        )
    return response, embed

def _chunk(number: int, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=UUID(f"18000000-0000-0000-0000-{number:012d}"),
        text=text,
        similarity_score=0.9,
    )
