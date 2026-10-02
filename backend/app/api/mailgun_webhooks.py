"""Public Mailgun webhook boundary; authentication is signature-based."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.services import mailgun_webhooks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/mailgun", status_code=200)
async def receive_mailgun_event(request: Request) -> dict[str, str]:
    try:
        payload: Any = await request.json()
    except Exception as exc:  # noqa: BLE001 - parser details are not exposed
        logger.warning("event=mailgun_webhook_rejected category=malformed_json")
        raise AppError(
            "Malformed webhook payload.",
            status_code=400,
            code="MAILGUN_WEBHOOK_MALFORMED",
        ) from exc
    try:
        event = mailgun_webhooks.parse_configured_event(payload)
    except AppError as exc:
        logger.warning(
            "event=mailgun_webhook_rejected category=%s",
            exc.code,
        )
        raise

    result = mailgun_webhooks.reconcile(get_admin_client(), event)
    outcome = str(result["result"])
    logger.info(
        "event=mailgun_webhook_processed provider=mailgun event_type=%s result=%s state_changed=%s",
        event.event_type,
        outcome,
        bool(result.get("state_changed")),
    )
    return {"status": "accepted"}

