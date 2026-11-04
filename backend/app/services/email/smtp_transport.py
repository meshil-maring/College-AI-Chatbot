"""Asynchronous, certificate-validated STARTTLS transport for Gmail SMTP."""

import asyncio
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import logging
import ssl

import aiosmtplib
from aiosmtplib import errors

from app.services.email.contracts import (
    DELIVERY_CONFIGURATION_ERROR, DELIVERY_PERMANENT_FAILURE,
    DELIVERY_TEMPORARY_FAILURE, DELIVERY_TIMEOUT, EmailDeliveryError,
    InvitationEmail, ProviderSendResult, normalize_provider_message_id,
)
from app.core.configuration.smtp import valid_mailbox

logger = logging.getLogger(__name__)


def _failure(code: str, *, retryable: bool = False) -> EmailDeliveryError:
    return EmailDeliveryError("Email could not be submitted.", code, retryable=retryable)


class SmtpEmailTransport:
    """No recipient allowlist; SMTP acceptance never confirms inbox delivery.

    SMTP has no idempotent send API. Retry only explicit transient rejections
    and failures before DATA; a lost DATA acknowledgement is non-retryable.
    """

    def __init__(self, *, host: str, port: int, username: str, password: str) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password.strip().replace(" ", "")

    def send_invitation(self, email: InvitationEmail, **kwargs) -> ProviderSendResult:
        """Existing FastAPI sync routes and the outbox run in worker threads."""
        return asyncio.run(self.send_invitation_async(email, **kwargs))

    async def send_invitation_async(
        self,
        email: InvitationEmail,
        *,
        from_address: str,
        reply_to: str | None,
        timeout_seconds: float,
        idempotency_key: str,
    ) -> ProviderSendResult:
        del idempotency_key  # Never publish internal attempt identifiers in headers.
        if not valid_mailbox(email.to_email):
            raise _failure(DELIVERY_PERMANENT_FAILURE)
        if not valid_mailbox(from_address, allow_display_name=True) or (
            reply_to and not valid_mailbox(reply_to, allow_display_name=True)
        ):
            raise _failure(DELIVERY_CONFIGURATION_ERROR)
        try:
            message = EmailMessage()
            message["From"] = from_address
            message["To"] = email.to_email
            message["Subject"] = email.subject
            message["Date"] = formatdate(localtime=False)
            message["Message-ID"] = make_msgid()
            if reply_to:
                message["Reply-To"] = reply_to
            message.set_content(email.body)
            if email.html_body:
                message.add_alternative(email.html_body, subtype="html")
        except (ValueError, TypeError):
            raise _failure(DELIVERY_PERMANENT_FAILURE) from None

        smtp = aiosmtplib.SMTP(
            hostname=self._host, port=self._port, timeout=timeout_seconds,
            use_tls=False, start_tls=True, validate_certs=True,
        )
        submitting = False
        try:
            # A total deadline also bounds DNS, TLS, login and DATA together.
            async with asyncio.timeout(timeout_seconds):
                await smtp.connect()
                await smtp.login(self._username, self._password)
                submitting = True
                refused, _ = await smtp.send_message(message, recipients=[email.to_email])
                if refused:
                    raise _failure(DELIVERY_PERMANENT_FAILURE)
        except errors.SMTPAuthenticationError:
            raise _failure(DELIVERY_CONFIGURATION_ERROR) from None
        except (ssl.SSLError, errors.SMTPNotSupported):
            raise _failure(DELIVERY_CONFIGURATION_ERROR) from None
        except errors.SMTPRecipientsRefused as exc:
            temporary = bool(exc.recipients) and all(
                400 <= recipient.code < 500 for recipient in exc.recipients
            )
            raise _failure(
                DELIVERY_TEMPORARY_FAILURE if temporary else DELIVERY_PERMANENT_FAILURE,
                retryable=temporary,
            ) from None
        except errors.SMTPResponseException as exc:
            temporary = 400 <= exc.code < 500
            raise _failure(
                DELIVERY_TEMPORARY_FAILURE if temporary else DELIVERY_PERMANENT_FAILURE,
                retryable=temporary,
            ) from None
        except (TimeoutError, errors.SMTPTimeoutError):
            raise _failure(DELIVERY_TIMEOUT, retryable=not submitting) from None
        except (OSError, errors.SMTPServerDisconnected, errors.SMTPConnectError):
            raise _failure(DELIVERY_TEMPORARY_FAILURE, retryable=not submitting) from None
        except errors.SMTPException:
            raise _failure(DELIVERY_PERMANENT_FAILURE) from None
        finally:
            # A failed QUIT must not turn an acknowledged submission into a
            # retry, nor mask the original error. Always close the socket.
            try:
                if smtp.is_connected:
                    await smtp.quit(timeout=min(timeout_seconds, 2.0))
            except (errors.SMTPException, OSError, TimeoutError):
                pass
            finally:
                smtp.close()

        logger.info("event=email_smtp_submitted provider=smtp")
        return ProviderSendResult(normalize_provider_message_id(message["Message-ID"]))
