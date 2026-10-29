"""Serve the actual application on an owned loopback port for live checks."""

from contextlib import contextmanager
import socket
import threading
import time

import httpx
import uvicorn


@contextmanager
def application():
    from app.main import app

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 30
        while not server.started:
            if not thread.is_alive() or time.monotonic() >= deadline:
                raise RuntimeError("Owned acceptance API did not start")
            time.sleep(0.1)
        origin = f"http://127.0.0.1:{port}"
        with httpx.Client(base_url=origin, timeout=120, trust_env=False) as api:
            yield api, origin
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        listener.close()
        if thread.is_alive():
            raise RuntimeError("Owned acceptance API did not stop")


def accepted(response, expected=200):
    if response.status_code != expected:
        try:
            failure = response.json()
            code = failure.get("error", {}).get("code") or failure.get("code")
        except (ValueError, AttributeError):
            code = None
        raise RuntimeError(f"{response.request.method} {response.request.url.path}: HTTP {response.status_code} ({code})")
    return response.json()
