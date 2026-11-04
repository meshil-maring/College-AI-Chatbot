"""Cross-field runtime validation shared by application settings."""

import logging
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

DEV_TEST_ENVIRONMENTS: frozenset[str] = frozenset(
    {"development", "dev", "local", "test", "testing"}
)


class SettingsValidation(BaseSettings):
    @model_validator(mode="after")
    def _dev_test_mode_requires_dev_environment(self) -> Self:
        """Fail closed when the dev-only authentication helpers are enabled
        outside a local development/testing environment (Phase 6.15.7).

        ``DEV_TEST_MODE=true`` exposes the development-only password
        recovery/reset endpoints (``app/api/auth/dev_auth.py``) and the matching
        frontend UI. A misconfigured deployment must NOT silently ship those
        endpoints, so the application refuses to start instead of running in
        an unsafe state. The check is allowlist-based: only the explicit local
        values in ``DEV_TEST_ENVIRONMENTS`` permit the flag, so a typo (or a
        new environment name) can never enable it by accident.

        Constructing ``Settings`` directly (tests, scripts) is unaffected —
        the validator only inspects the two values that were resolved.
        """
        environment = (self.environment or "").strip().lower()
        if not self.dev_test_mode:
            return self
        if environment not in DEV_TEST_ENVIRONMENTS:
            raise ValueError(
                "DEV_TEST_MODE cannot be enabled outside a local "
                "development/testing environment. Set ENVIRONMENT to one of "
                f"{sorted(DEV_TEST_ENVIRONMENTS)} or set DEV_TEST_MODE=false. "
                "Refusing to start so that the development-only password "
                "recovery endpoints can never be exposed in a deployed "
                "environment."
            )
        logger.warning(
            "DEV_TEST_MODE is enabled (ENVIRONMENT=%s): development-only "
            "password recovery/reset endpoints are exposed. Never enable this "
            "outside local development/testing.",
            environment,
        )
        return self

    @model_validator(mode="after")
    def _validate_public_resource_controls(self) -> Self:
        if self.public_institution_concurrency_limit > self.public_concurrency_limit:
            raise ValueError(
                "PUBLIC_INSTITUTION_CONCURRENCY_LIMIT must not exceed "
                "PUBLIC_CONCURRENCY_LIMIT"
            )
        if self.public_max_body_bytes <= self.public_max_message_chars:
            raise ValueError(
                "PUBLIC_MAX_BODY_BYTES must leave room for the JSON request envelope"
            )
        if self.email_provider_retry_base_seconds > self.email_provider_retry_cap_seconds:
            raise ValueError(
                "EMAIL_PROVIDER_RETRY_BASE_SECONDS must not exceed "
                "EMAIL_PROVIDER_RETRY_CAP_SECONDS"
            )
        return self
