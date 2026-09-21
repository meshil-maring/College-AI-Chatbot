"""Physical validation — registration failures must never kill the server.

Runs the REAL FastAPI application in a REAL uvicorn process and verifies:

    1. GET  /health                          -> 200 (server up)
    2. POST /api/v1/users/register (DB down) -> controlled 5xx, no traceback
    3. GET  /health                          -> 200 (STILL ALIVE)
    4. GET  /                                 -> 200 (still serving other routes)
    5. POST /api/v1/users/register (DB down) -> controlled 5xx again
    6. GET  /health                          -> 200 (still alive)
    7. The server log contains the real exception (debuggable server-side)
       and no "Exception in ASGI application" (the request never escaped the
       application's controlled error handling).

The Supabase URL is overridden to an unreachable local port for the duration
of the run, so the database layer fails exactly like an outage would while NO
production data is read or written.

Usage (from ``backend/``):

    python scripts/validation/test_registration_resilience.py [port]
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time

# Resolve the backend package root so the script runs from any working directory.
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND_ROOT)

import httpx  # noqa: E402  (import after the sys.path bootstrap, like the other scripts)

UNREACHABLE_SUPABASE_URL = "http://127.0.0.1:9/"
STARTUP_TIMEOUT_SECONDS = 60

REGISTRATION_PAYLOAD = {
    "registration_type": "student",
    "institution_code": "IMPHAL",
    "email": "resilience.probe@example.com",
    "password": "probe-password-123",
    "first_name": "Resilience",
    "last_name": "Probe",
    "register_number": "RESILIENCE-1",
    "university_roll_number": "RESILIENCE-1",
}

RESULTS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((label, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))


def _server_env() -> dict:
    env = dict(os.environ)
    # Point the application at a port nothing listens on: every database call
    # fails at the transport layer, so the registration hits the controlled
    # failure path without touching real data.
    env["SUPABASE_URL"] = UNREACHABLE_SUPABASE_URL
    env["ENVIRONMENT"] = "development"
    return env


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    base_url = f"http://127.0.0.1:{port}"
    log_path = os.path.join(
        tempfile.gettempdir(), f"registration_resilience_{port}.log"
    )
    log_file = open(log_path, "w", encoding="utf-8", errors="replace")

    print("=" * 74)
    print("Registration resilience — live uvicorn process")
    print(f"  port          : {port}")
    print(f"  database URL  : {UNREACHABLE_SUPABASE_URL} (deliberately unreachable)")
    print(f"  server log    : {log_path}")
    print("=" * 74)

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=BACKEND_ROOT,
        env=_server_env(),
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    try:
        with httpx.Client(base_url=base_url, timeout=30) as client:
            ready = False
            deadline = time.time() + STARTUP_TIMEOUT_SECONDS
            while time.time() < deadline:
                if process.poll() is not None:
                    break
                try:
                    if client.get("/health").status_code == 200:
                        ready = True
                        break
                except Exception:  # noqa: BLE001 - server not accepting yet
                    time.sleep(0.5)
            check("1. Server started and /health responds 200", ready)
            if not ready:
                return 1

            response = client.post("/api/v1/users/register", json=REGISTRATION_PAYLOAD)
            body = response.text
            check(
                "2. Failing registration returns a controlled 5xx",
                response.status_code == 500
                and response.json().get("error", {}).get("code")
                == "REGISTRATION_FAILED",
                f"status={response.status_code} body={body[:160]}",
            )
            check(
                "3. Response leaks no traceback / internal detail / credential",
                "traceback" not in body.lower()
                and "attributerror" not in body.lower()
                and "nonetype" not in body.lower()
                and "supabase" not in body.lower()
                and REGISTRATION_PAYLOAD["password"] not in body,
            )

            health = client.get("/health")
            check(
                "4. /health still works right after the failure",
                health.status_code == 200 and health.json().get("status") == "ok",
                f"status={health.status_code}",
            )

            root = client.get("/")
            check(
                "5. Other endpoints still work",
                root.status_code == 200,
                f"status={root.status_code}",
            )

            second = client.post("/api/v1/users/register", json=REGISTRATION_PAYLOAD)
            check(
                "6. Another registration request is still processed",
                second.status_code == 500
                and second.json().get("error", {}).get("code")
                == "REGISTRATION_FAILED",
                f"status={second.status_code}",
            )

            health_after = client.get("/health")
            check(
                "7. Server process still running after repeated failures",
                health_after.status_code == 200 and process.poll() is None,
                f"status={health_after.status_code} exit_code={process.poll()}",
            )
    finally:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:  # pragma: no cover - defensive
            process.kill()
        log_file.close()

    log = open(log_path, "r", encoding="utf-8", errors="replace").read()
    check(
        "8. Server log records the real exception server-side",
        "User registration failed (unexpected error)" in log
        and "Traceback (most recent call last)" in log,
    )
    check(
        "9. No unhandled exception escaped the application",
        "Exception in ASGI application" not in log
        and "Unhandled server error on /api/v1/users/register" not in log,
    )
    check(
        "10. Log contains no password",
        REGISTRATION_PAYLOAD["password"] not in log,
    )

    print("-" * 74)
    print("Server log (tail):")
    for line in log.splitlines()[-12:]:
        print(f"    {line}")
    print("-" * 74)

    failed = [label for label, ok, _ in RESULTS if not ok]
    print(f"RESULT: {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
        return 1
    print("PASS — registration failures are controlled and the server stays alive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

