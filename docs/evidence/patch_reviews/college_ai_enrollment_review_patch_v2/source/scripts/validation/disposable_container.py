"""Fail-closed validation for disposable, isolated PostgreSQL test containers.

This module never creates containers or connects to a database. Callers must pass
an exact container ID and run token emitted by their own local-only runner.
"""
from __future__ import annotations

import json
import os
import re
import subprocess

EXPECTED_IMAGE = "public.ecr.aws/supabase/postgres:17.6.1.166"
ALLOWED_PURPOSES = {"academic-setup", "faculty-attendance", "faculty-tests", "faculty-assignment"}


def command(args: list[str], **kwargs):
    return subprocess.run(args, capture_output=True, text=True, timeout=20, **kwargs)


def validate_disposable_target(container_id: str, run_token: str, purpose: str) -> str:
    """Return container ID only when the target is an isolated run-owned container."""
    if os.environ.get("DOCKER_HOST"):
        raise RuntimeError("DOCKER_HOST overrides are prohibited for validation")
    if not re.fullmatch(r"[a-f0-9]{64}", container_id or ""):
        raise RuntimeError("Pass the full 64-character container ID emitted by the runner")
    if not re.fullmatch(r"[a-f0-9]{32}", run_token or ""):
        raise RuntimeError("Invalid validation run token")
    if purpose not in ALLOWED_PURPOSES:
        raise RuntimeError("Unrecognized disposable validation purpose")

    context = command(["docker", "context", "show"])
    if context.returncode or context.stdout.strip() != "desktop-linux":
        raise RuntimeError("Only Docker Desktop's local desktop-linux context is allowed")
    engine = command(["docker", "info", "--format", "{{.Name}}"])
    if engine.returncode or engine.stdout.strip() != "docker-desktop":
        raise RuntimeError("Expected the local Docker Desktop engine")
    inspected = command(["docker", "inspect", container_id])
    if inspected.returncode:
        raise RuntimeError("The supplied container ID cannot be inspected")
    objects = json.loads(inspected.stdout)
    if len(objects) != 1:
        raise RuntimeError("Expected exactly one inspected container")
    container = objects[0]
    labels = container.get("Config", {}).get("Labels") or {}
    if container.get("Id") != container_id:
        raise RuntimeError("Docker returned a different container ID")
    if container.get("State", {}).get("Running") is not True:
        raise RuntimeError("Disposable validation container is not running")
    if container.get("Config", {}).get("Image") != EXPECTED_IMAGE:
        raise RuntimeError("Unexpected PostgreSQL image")
    if labels.get("collegeai.validation.disposable") != "true":
        raise RuntimeError("Disposable validation label is missing")
    if labels.get("collegeai.validation.run") != run_token:
        raise RuntimeError("Run token does not match this container")
    if labels.get("collegeai.validation.purpose") != purpose:
        raise RuntimeError("Validation purpose does not match this container")
    host = container.get("HostConfig", {})
    mounts = container.get("Mounts") or []
    # The only permitted storage is a bounded in-memory tmpfs over PostgreSQL's
    # data directory. No named/anonymous volumes or bind mounts are accepted.
    if len(mounts) != 1 or mounts[0].get("Type") != "tmpfs" or mounts[0].get("Destination") != "/var/lib/postgresql/data":
        raise RuntimeError("Expected only the PostgreSQL data-directory tmpfs; persistent mounts are prohibited")
    if host.get("Binds") or set((host.get("Tmpfs") or {}).keys()) != {"/var/lib/postgresql/data"}:
        raise RuntimeError("Unexpected bind or tmpfs mount configuration")
    if host.get("AutoRemove") is not True:
        raise RuntimeError("Disposable containers must be created with --rm")
    bindings = host.get("PortBindings") or {}
    if any(values for values in bindings.values()):
        raise RuntimeError("Database containers with published host ports are prohibited")
    if host.get("NetworkMode") != "none":
        raise RuntimeError("Disposable validation containers must use Docker network=none")
    return container_id
