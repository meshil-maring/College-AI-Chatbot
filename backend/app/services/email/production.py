"""Bounded provider delivery, retry policy, and safe health reporting."""

import asyncio
import logging
import time
from typing import Callable

from app.config import settings
from app.services.email.contracts import (
    DELIVERY_CONFIGURATION_ERROR, DELIVERY_MALFORMED_RESPONSE, DELIVERY_SENT,
    DELIVERY_TEMPORARY_FAILURE, DELIVERY_TIMEOUT, EmailDeliveryError,
    EmailDeliveryResult, InvitationEmail, ProductionEmailTransport, ProviderHealth,
    ProviderHealthState, ProviderSendResult,
)

logger = logging.getLogger(__name__)

class ProductionEmailProvider:
    """Reliable provider-neutral production delivery boundary.

    The same idempotency key is sent on every bounded retry. The transport must
    apply that key using its provider's idempotency mechanism. If a selected
    provider cannot guarantee this, its adapter must classify uncertain errors
    as non-retryable to avoid duplicate mail.
    """

    name = "production"

    def __init__(
        self,
        *,
        provider_name: str,
        from_address: str,
        reply_to: str | None = None,
        transport: ProductionEmailTransport | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        retry_base_seconds: float | None = None,
        retry_cap_seconds: float | None = None,
        api_key: str | None = None,
        requires_api_key: bool = True,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._provider_name = provider_name
        self.name = provider_name or "production"
        self._requires_api_key = requires_api_key
        self._from_address = from_address
        self._reply_to = reply_to
        self._api_key = (
            settings.email_provider_api_key if api_key is None else api_key
        ).strip()
        self._transport = transport
        self._timeout_seconds = (
            settings.email_provider_timeout_seconds
            if timeout_seconds is None
            else timeout_seconds
        )
        self._max_retries = (
            settings.email_provider_max_retries if max_retries is None else max_retries
        )
        self._retry_base_seconds = (
            settings.email_provider_retry_base_seconds
            if retry_base_seconds is None
            else retry_base_seconds
        )
        self._retry_cap_seconds = (
            settings.email_provider_retry_cap_seconds
            if retry_cap_seconds is None
            else retry_cap_seconds
        )
        self._sleep = sleep
        self._health_state = (
            ProviderHealthState.CONFIGURED
            if self.is_configured
            else ProviderHealthState.NOT_CONFIGURED
        )

    @property
    def is_configured(self) -> bool:
        return (
            bool(self._provider_name.strip())
            and (not self._requires_api_key or bool(self._api_key))
            and bool(self._from_address.strip())
            and self._transport is not None
        )

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            state=self._health_state,
            provider=self._provider_name or self.name,
        )

    def _retry_delay(self, retry_index: int, exc: EmailDeliveryError) -> float:
        if exc.retry_after_seconds is not None:
            return min(max(exc.retry_after_seconds, 0.0), self._retry_cap_seconds)
        return min(
            self._retry_base_seconds * (2 ** max(0, retry_index - 1)),
            self._retry_cap_seconds,
        )

    def send_invitation(self, email: InvitationEmail) -> EmailDeliveryResult:
        if not self.is_configured or not email.idempotency_key:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_CONFIGURATION_ERROR,
            )

        started = time.monotonic()
        for attempt in range(self._max_retries + 1):
            try:
                response = self._transport.send_invitation(
                    email,
                    from_address=self._from_address,
                    reply_to=self._reply_to,
                    timeout_seconds=self._timeout_seconds,
                    idempotency_key=email.idempotency_key,
                )
                if (
                    not isinstance(response, ProviderSendResult)
                    or not response.message_id.strip()
                ):
                    raise EmailDeliveryError(
                        "Invitation could not be delivered.",
                        code=DELIVERY_MALFORMED_RESPONSE,
                    )
                logger.info(
                    "event=admin_invitation_email_sent provider=%s attempts=%d duration_ms=%d",
                    self._provider_name,
                    attempt + 1,
                    int((time.monotonic() - started) * 1000),
                )
                self._health_state = ProviderHealthState.CONFIGURED
                return EmailDeliveryResult(
                    DELIVERY_SENT,
                    self._provider_name,
                    provider_message_id=response.message_id,
                )
            except TimeoutError:
                exc = EmailDeliveryError(
                    "Invitation could not be delivered.",
                    code=DELIVERY_TIMEOUT,
                    retryable=True,
                )
            except OSError:
                exc = EmailDeliveryError(
                    "Invitation could not be delivered.",
                    code=DELIVERY_TEMPORARY_FAILURE,
                    retryable=True,
                )
            except EmailDeliveryError as error:
                exc = error

            if not exc.retryable or attempt >= self._max_retries:
                if exc.retryable:
                    self._health_state = ProviderHealthState.TEMPORARILY_UNAVAILABLE
                raise exc
            delay = self._retry_delay(attempt + 1, exc)
            logger.warning(
                "event=admin_invitation_email_retry provider=%s code=%s retry=%d delay_ms=%d",
                self._provider_name,
                exc.code,
                attempt + 1,
                int(delay * 1000),
            )
            self._sleep(delay)

        raise AssertionError("bounded email retry loop exhausted unexpectedly")

    async def send_invitation_async(self, email: InvitationEmail) -> EmailDeliveryResult:
        """Keep synchronous transports and retry sleeps off the ASGI event loop."""
        return await asyncio.to_thread(self.send_invitation, email)
