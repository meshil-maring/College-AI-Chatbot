"""Mailgun HTTP transport retained for switching providers later."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import httpx

from app.services.email.contracts import (
    DELIVERY_CONFIGURATION_ERROR, DELIVERY_MALFORMED_RESPONSE,
    DELIVERY_PERMANENT_FAILURE, DELIVERY_RATE_LIMITED, DELIVERY_TEMPORARY_FAILURE,
    DELIVERY_TIMEOUT, EmailDeliveryError, InvitationEmail, ProviderSendResult,
    normalize_provider_message_id,
)

def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value.strip()))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


class MailgunEmailTransport:
    """Mailgun HTTP API adapter below the provider-neutral boundary."""

    def __init__(
        self,
        *,
        api_key: str,
        domain: str,
        base_url: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self._domain = domain.strip()
        self._base_url = base_url.strip().rstrip("/")
        self._client = client

    def _request(
        self, url: str, data: dict[str, str], timeout_seconds: float
    ) -> httpx.Response:
        kwargs = {
            "auth": ("api", self._api_key),
            # `(None, value)` makes httpx emit a multipart text field, matching
            # Mailgun's documented Messages API contract.
            "files": {name: (None, value) for name, value in data.items()},
            "timeout": timeout_seconds,
        }
        if self._client is not None:
            return self._client.post(url, **kwargs)
        with httpx.Client() as client:
            return client.post(url, **kwargs)

    def send_invitation(
        self,
        email: InvitationEmail,
        *,
        from_address: str,
        reply_to: str | None,
        timeout_seconds: float,
        idempotency_key: str,
    ) -> ProviderSendResult:
        # Mailgun's Messages API has no general send idempotency key. The
        # stable application key remains useful for local attempt identity but
        # is deliberately not placed in message headers/user variables (which
        # would expose an internal identifier in the delivered message).
        del idempotency_key
        if not all((self._api_key, self._domain, self._base_url, from_address.strip())):
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_CONFIGURATION_ERROR,
            )
        url = f"{self._base_url}/v3/{quote(self._domain, safe='.')}/messages"
        form = {
            "from": from_address,
            "to": email.to_email,
            "subject": email.subject,
            "text": email.body,
        }
        if email.html_body:
            form["html"] = email.html_body
        if reply_to:
            form["h:Reply-To"] = reply_to
        try:
            response = self._request(url, form, timeout_seconds)
        except httpx.TimeoutException as exc:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_TIMEOUT,
                retryable=True,
            ) from exc
        except httpx.TransportError as exc:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_TEMPORARY_FAILURE,
                retryable=True,
            ) from exc

        if response.status_code == 429:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_RATE_LIMITED,
                retryable=True,
                retry_after_seconds=_retry_after_seconds(response.headers.get("Retry-After")),
                provider_status_code=response.status_code,
            )
        if response.status_code in {401, 403}:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_CONFIGURATION_ERROR,
                provider_status_code=response.status_code,
            )
        if 500 <= response.status_code <= 599:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_TEMPORARY_FAILURE,
                retryable=True,
                provider_status_code=response.status_code,
            )
        if response.status_code != 200:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_PERMANENT_FAILURE,
                provider_status_code=response.status_code,
            )
        try:
            payload = response.json()
        except (ValueError, TypeError) as exc:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_MALFORMED_RESPONSE,
            ) from exc
        message_id = normalize_provider_message_id(
            payload.get("id", "") if isinstance(payload, dict) else ""
        )
        if not message_id:
            raise EmailDeliveryError(
                "Invitation could not be delivered.",
                code=DELIVERY_MALFORMED_RESPONSE,
            )
        return ProviderSendResult(message_id=message_id)
