from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "College AI Chatbot API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    supabase_url: str = ""
    supabase_publishable_key: str = ""
    supabase_secret_key: str = ""
    supabase_jwks_url: str = ""

    max_upload_size_mb: int = 50

    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket: str = "documents"

    ai_provider: str = "openrouter"
    openrouter_api_key: str = ""
    openrouter_site_url: str = ""
    openrouter_app_name: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"
    embedding_model: str = "qwen/qwen3-embedding-8b"
    embedding_dimensions: int = 1536
    embedding_batch_size: int = 100

    # Phase 5.7b — bounded multi-turn conversational context.
    # Maximum number of persisted messages (user+assistant combined) included
    # in the generation context for an existing conversation.
    conversation_history_max_messages: int = 10

    # ------------------------------------------------------------------
    # DEVELOPMENT / TESTING ONLY.
    #
    # Gates the dev-only password recovery/reset feature (see
    # app/api/dev_auth.py). Must be `False` (the default) everywhere except
    # a local development/testing environment. Never enable in production.
    # ------------------------------------------------------------------
    dev_test_mode: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()