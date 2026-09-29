"""Process-local resource controls for the anonymous public chat endpoint.

The project currently runs as one Uvicorn process and has no Redis/gateway
limiter.  These controls are therefore intentionally dependency-free and
thread-safe, but each worker has independent state.  A distributed edge/store
is still required before scaling the backend horizontally.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Callable

from app.config import settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)


class SlidingWindowRateLimiter:
    """Atomic, bounded sliding-window counters for several dimensions."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(
        self,
        rules: list[tuple[str, str, int]],
        window_seconds: int,
    ) -> int | None:
        now = self._clock()
        cutoff = now - window_seconds
        with self._lock:
            # Sweep all expired identities, not just identities present in
            # this request. This keeps rotating institution codes/IPs from
            # becoming permanent process memory.
            for key, events in list(self._events.items()):
                while events and events[0] <= cutoff:
                    events.popleft()
                if not events:
                    self._events.pop(key, None)
            retry_after = 0
            for scope, identity, limit in rules:
                events = self._events[(scope, identity)]
                while events and events[0] <= cutoff:
                    events.popleft()
                if len(events) >= limit:
                    retry_after = max(
                        retry_after,
                        max(1, math.ceil(events[0] + window_seconds - now)),
                    )
            if retry_after:
                return retry_after
            for scope, identity, _limit in rules:
                self._events[(scope, identity)].append(now)
        return None

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


@dataclass
class ConcurrencyLease:
    _gate: "PublicConcurrencyGate"
    institution_code: str
    _released: bool = False

    def release(self) -> None:
        if not self._released:
            self._released = True
            self._gate.release(self.institution_code)


class PublicConcurrencyGate:
    """Non-blocking global and per-institution concurrency accounting."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._global_active = 0
        self._institution_active: dict[str, int] = defaultdict(int)

    def try_acquire(self, institution_code: str) -> ConcurrencyLease | None:
        with self._lock:
            if self._global_active >= settings.public_concurrency_limit:
                return None
            if (
                self._institution_active[institution_code]
                >= settings.public_institution_concurrency_limit
            ):
                return None
            self._global_active += 1
            self._institution_active[institution_code] += 1
        return ConcurrencyLease(self, institution_code)

    def release(self, institution_code: str) -> None:
        with self._lock:
            if (
                self._global_active <= 0
                or self._institution_active[institution_code] <= 0
            ):
                logger.error("event=public_concurrency_accounting_error")
                return
            self._global_active -= 1
            self._institution_active[institution_code] -= 1
            if self._institution_active[institution_code] == 0:
                self._institution_active.pop(institution_code, None)

    def reset(self) -> None:
        with self._lock:
            self._global_active = 0
            self._institution_active.clear()


rate_limiter = SlidingWindowRateLimiter()
concurrency_gate = PublicConcurrencyGate()


def enforce_rate_limit(client_identity: str, institution_code: str) -> None:
    """Charge one request atomically across client, tenant, and global scopes."""
    if not settings.public_rate_limit_enabled:
        return
    retry_after = rate_limiter.check(
        [
            ("client", client_identity, settings.public_rate_limit_requests),
            (
                "institution",
                institution_code,
                settings.public_institution_rate_limit_requests,
            ),
            ("global", "public-chat", settings.public_global_rate_limit_requests),
        ],
        settings.public_rate_limit_window_seconds,
    )
    if retry_after is None:
        return
    logger.warning(
        "event=public_rate_limited institution=%s status=429",
        institution_code,
    )
    raise AppError(
        "The public chatbot is busy. Please try again shortly.",
        status_code=429,
        code="PUBLIC_RATE_LIMITED",
        headers={"Retry-After": str(retry_after)},
    )


def acquire_concurrency(institution_code: str) -> ConcurrencyLease:
    lease = concurrency_gate.try_acquire(institution_code)
    if lease is not None:
        return lease
    logger.warning(
        "event=public_concurrency_rejected institution=%s status=503",
        institution_code,
    )
    raise AppError(
        "The public chatbot is busy. Please try again shortly.",
        status_code=503,
        code="PUBLIC_CHAT_BUSY",
        headers={"Retry-After": str(settings.public_overload_retry_after_seconds)},
    )


def reset_public_abuse_state() -> None:
    """Test hook; production code never resets enforcement state."""
    rate_limiter.reset()
    concurrency_gate.reset()
