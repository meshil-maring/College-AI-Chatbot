"""Disposable database commands and readiness for historical reset validation."""

import subprocess
import time

from disposable_container import docker_arguments


def docker(*args: str, sql: str | None = None, expect_success: bool = True) -> str:
    result = subprocess.run(
        docker_arguments(*args),
        input=sql,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if expect_success and result.returncode != 0:
        raise RuntimeError(f"Docker verification failed: {result.stderr[-2000:]}")
    if not expect_success and result.returncode == 0:
        raise AssertionError("Expected SQL refusal, but the operation succeeded")
    return result.stdout.strip()


def wait_database(execute, container_id):
    for _ in range(100):
        process = docker("exec", container_id, "cat", "/proc/1/comm")

        readiness = subprocess.run(
            docker_arguments(
                "exec",
                container_id,
                "pg_isready",
                "-U",
                "postgres",
            ),
            capture_output=True,
            text=True,
            check=False,
        )

        # The cached image uses a .postgres wrapper process name. Match

        # the established Faculty verifier's prefix check, not equality.

        if readiness.returncode == 0 and process.strip().lstrip(".").startswith(
            "postgres"
        ):
            execute("SELECT 1;")

            break

        time.sleep(0.5)

    else:
        raise RuntimeError("Disposable PostgreSQL did not finish initialization")
