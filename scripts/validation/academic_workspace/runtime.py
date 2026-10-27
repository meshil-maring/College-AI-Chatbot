"""Owned, network-isolated PostgreSQL for realistic Academic Setup validation."""

from contextlib import contextmanager
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/validation"))

from disposable_container import (
    EXPECTED_IMAGE, docker_arguments, expected_name, validate_cleanup_target,
    validate_disposable_target, validate_local_engine,
)


def checked(arguments, *, sql=None, timeout=180):
    result = subprocess.run(
        arguments, input=sql, capture_output=True, text=True, timeout=timeout,
        encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError(result.stderr[-10000:] or result.stdout[-10000:])
    return result.stdout.strip()


def sql_arguments(container):
    return docker_arguments(
        "exec", "-i", container, "psql", "-X", "-U", "postgres", "-d", "postgres",
        "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=verbose", "-Atq",
    )


def execute(container, sql):
    return checked(sql_arguments(container), sql=sql)


@contextmanager
def database():
    validate_local_engine()
    token, purpose, container = uuid4().hex, "academic-setup", None
    try:
        container = checked(docker_arguments(
            "run", "--pull=never", "--rm", "-d", "--network", "none",
            "--tmpfs", "/var/lib/postgresql/data:rw,size=536870912",
            "--name", expected_name(token, purpose),
            "--label", "collegeai.validation.disposable=true",
            "--label", f"collegeai.validation.run={token}",
            "--label", f"collegeai.validation.purpose={purpose}",
            "-e", "PGDATA=/var/lib/postgresql/data",
            "-e", f"POSTGRES_PASSWORD={uuid4().hex}", EXPECTED_IMAGE,
        ))
        if not re.fullmatch(r"[a-f0-9]{64}", container):
            raise RuntimeError("Expected full run-owned container ID")
        validate_disposable_target(container, token, purpose)
        print("START: owned local PostgreSQL; waiting for database initialization", flush=True)
        for _ in range(60):
            try:
                result = subprocess.run(
                    docker_arguments("exec", container, "pg_isready", "-U", "postgres"),
                    capture_output=True, timeout=30,
                )
            except subprocess.TimeoutExpired:
                continue
            if not result.returncode:
                process = checked(docker_arguments("exec", container, "cat", "/proc/1/comm"))
                if re.match(r"^\.?postgres(?:-|$)", process):
                    break
            time.sleep(0.5)
        else:
            raise RuntimeError("Local PostgreSQL did not become ready")
        yield container
    finally:
        if container and re.fullmatch(r"[a-f0-9]{64}", container):
            validate_cleanup_target(container, token, purpose)
            checked(docker_arguments("stop", "--timeout", "10", container))


def replay(container):
    paths = sorted((ROOT / "supabase/migrations").glob("*.sql"))
    checked(docker_arguments("cp", str(ROOT / "supabase/migrations"), f"{container}:/tmp/migrations"))
    for path in paths:
        print(f"REPLAY {path.name}", flush=True)
        checked(docker_arguments(
            "exec", container, "psql", "-X", "-U", "postgres", "-d", "postgres",
            "-v", "ON_ERROR_STOP=1", "-q", "-f", f"/tmp/migrations/{path.name}",
        ))
    print(f"PASS: {len(paths)} migrations replayed through {paths[-1].name}", flush=True)


def run_file(container, name):
    output = execute(container, (Path(__file__).parent / name).read_text(encoding="utf-8"))
    if output:
        print(output, flush=True)
