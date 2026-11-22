"""Development-only background loop that sends queued invitation emails.

The repository has no scheduler for the email outbox: deployments run
``EmailOutboxWorker.process_once`` on their own schedule. For local work,
``EMAIL_OUTBOX_WORKER_INLINE=true`` lets the backend process run that worker
every ``EMAIL_OUTBOX_WORKER_INTERVAL_SECONDS``. It is refused outside local and
test environments, so a deployment never depends on it by accident. Claiming
happens in PostgreSQL, so it is safe next to any other worker.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from app.services.email.email_outbox_worker import EmailOutboxWorker

logger = logging.getLogger(__name__)


def inline_worker_enabled(settings: Any) -> bool:
    """On only when asked for, and only in a local or test environment."""
    if not getattr(settings, "email_outbox_worker_inline", False):
        return False
    if not getattr(settings, "is_local_environment", False):
        logger.warning("event=email_outbox_inline_worker_refused reason=non_local_environment")
        return False
    return True


async def run_inline_worker(
    interval_seconds: float,
    stop: asyncio.Event,
    process_once: Callable[[], Any] | None = None,
) -> None:
    """Send queued emails until ``stop`` is set; one failed pass never ends the loop."""
    process = process_once or EmailOutboxWorker().process_once
    while not stop.is_set():
        try:
            await asyncio.to_thread(process)
        except Exception:  # noqa: BLE001 - keep the dev loop alive; details are logged
            logger.exception("event=email_outbox_inline_worker_failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass


def attach_inline_worker(app: Any, settings: Any) -> None:
    """Start the loop with the application and stop it on shutdown, when enabled."""
    if not inline_worker_enabled(settings):
        return
    state: dict[str, Any] = {}

    async def start() -> None:
        state["stop"] = asyncio.Event()
        state["task"] = asyncio.create_task(
            run_inline_worker(settings.email_outbox_worker_interval_seconds, state["stop"])
        )
        logger.info("event=email_outbox_inline_worker_started")

    async def stop() -> None:
        if "stop" in state:
            state["stop"].set()
            await state["task"]

    app.router.add_event_handler("startup", start)
    app.router.add_event_handler("shutdown", stop)
