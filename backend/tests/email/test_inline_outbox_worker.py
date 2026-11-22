"""The development-only inline email outbox worker."""

import asyncio
import time
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.email import inline_outbox_worker as inline


def settings(enabled=True, local=True):
    return SimpleNamespace(email_outbox_worker_inline=enabled, is_local_environment=local,
                           email_outbox_worker_interval_seconds=1.0)


def test_off_by_default_and_refused_outside_local_environments():
    assert not inline.inline_worker_enabled(settings(enabled=False))
    assert not inline.inline_worker_enabled(settings(local=False))
    assert inline.inline_worker_enabled(settings())


def test_disabled_worker_registers_nothing():
    app = FastAPI()
    before = (len(app.router.on_startup), len(app.router.on_shutdown))
    inline.attach_inline_worker(app, settings(enabled=False))
    inline.attach_inline_worker(app, settings(local=False))
    assert (len(app.router.on_startup), len(app.router.on_shutdown)) == before


def test_loop_keeps_sending_after_a_failed_pass_and_stops_cleanly():
    calls = []

    def process():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("provider down")

    async def scenario():
        stop = asyncio.Event()
        task = asyncio.create_task(inline.run_inline_worker(0.01, stop, process))
        while len(calls) < 3:
            await asyncio.sleep(0.01)
        stop.set()
        await asyncio.wait_for(task, timeout=1)

    asyncio.run(scenario())
    assert len(calls) >= 3


def test_application_starts_and_stops_the_worker(monkeypatch):
    passes = []
    monkeypatch.setattr(inline.EmailOutboxWorker, "process_once", lambda self: passes.append(1))
    app = FastAPI()
    inline.attach_inline_worker(app, settings())

    with TestClient(app):  # runs the real startup and shutdown hooks
        deadline = time.monotonic() + 2
        while not passes and time.monotonic() < deadline:
            time.sleep(0.01)
    assert passes


def test_the_real_application_never_runs_the_worker_under_tests():
    from app.main import app as main_app

    handlers = [*main_app.router.on_startup, *main_app.router.on_shutdown]
    assert not any(getattr(h, "__module__", "") == inline.__name__ for h in handlers)
