"""Local-only, run-owned Docker target checks. Never opens a database."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess

EXPECTED_IMAGE = "public.ecr.aws/supabase/postgres:17.6.1.166"
DATA_DIRECTORY = "/var/lib/postgresql/data"
MAX_TMPFS_BYTES = 536870912
ALLOWED_PURPOSES = {
    "academic-setup", "faculty-attendance", "faculty-tests", "faculty-assignment",
    "data-reset", "knowledge-resources",
}
DOCKER_CONTEXT = "desktop-linux"
LOCAL_ENDPOINT = "npipe:////./pipe/dockerDesktopLinuxEngine"


def docker_arguments(*args: str) -> list[str]:
    if os.environ.get("DOCKER_HOST"):
        raise RuntimeError("DOCKER_HOST overrides are prohibited for validation")
    if os.environ.get("DOCKER_CONTEXT") not in (None, "", DOCKER_CONTEXT):
        raise RuntimeError("DOCKER_CONTEXT overrides are prohibited for validation")
    return ["docker", "--context", DOCKER_CONTEXT, *args]


def command(args: list[str], **kwargs):
    return subprocess.run(args, capture_output=True, text=True, timeout=20, **kwargs)


def validate_local_engine() -> None:
    docker_arguments()  # Reject overrides before even inspecting context state.
    context = command(["docker", "context", "show"])
    if context.returncode or context.stdout.strip() != DOCKER_CONTEXT:
        raise RuntimeError("Only the local desktop-linux context is allowed")
    endpoint = command(docker_arguments("context", "inspect", DOCKER_CONTEXT))
    if endpoint.returncode:
        raise RuntimeError("Cannot inspect the local Docker context")
    contexts = json.loads(endpoint.stdout)
    if not isinstance(contexts, list) or len(contexts) != 1:
        raise RuntimeError("Expected exactly one Docker context")
    if contexts[0].get("Endpoints", {}).get("docker", {}).get("Host") != LOCAL_ENDPOINT:
        raise RuntimeError("Expected the local Docker Desktop Linux named pipe")
    engine = command(docker_arguments("info", "--format", "{{.Name}} {{.OSType}}"))
    if engine.returncode or engine.stdout.strip() != "docker-desktop linux":
        raise RuntimeError("Expected the local Docker Desktop Linux engine")


def expected_name(run_token: str, purpose: str) -> str:
    return f"codex-{purpose}-{run_token[:12]}"


def validate_arguments(container_id: str, run_token: str, purpose: str) -> None:
    if not re.fullmatch(r"[a-f0-9]{64}", container_id or ""):
        raise RuntimeError("Pass the full 64-character container ID emitted by the runner")
    if not re.fullmatch(r"[a-f0-9]{32}", run_token or ""):
        raise RuntimeError("Invalid validation run token")
    if purpose not in ALLOWED_PURPOSES:
        raise RuntimeError("Unrecognized disposable validation purpose")


def owned_container(container_id: str, run_token: str, purpose: str) -> dict:
    """Inspect ownership by full ID and fresh token; never resolve names/aliases."""
    validate_arguments(container_id, run_token, purpose)
    validate_local_engine()
    inspected = command(docker_arguments("inspect", container_id))
    if inspected.returncode:
        raise RuntimeError("The supplied container ID cannot be inspected")
    objects = json.loads(inspected.stdout)
    if not isinstance(objects, list) or len(objects) != 1 or not isinstance(objects[0], dict):
        raise RuntimeError("Expected exactly one inspected container")
    container = objects[0]
    config = container.get("Config") or {}
    labels = config.get("Labels") or {}
    if container.get("Id") != container_id:
        raise RuntimeError("Docker returned a different container ID")
    if container.get("Name") != "/" + expected_name(run_token, purpose):
        raise RuntimeError("Unexpected container name; persistent project targets are prohibited")
    if config.get("Image") != EXPECTED_IMAGE:
        raise RuntimeError("Unexpected PostgreSQL image")
    if labels.get("collegeai.validation.disposable") != "true":
        raise RuntimeError("Disposable validation label is missing")
    if labels.get("collegeai.validation.run") != run_token:
        raise RuntimeError("Run token does not match this container")
    if labels.get("collegeai.validation.purpose") != purpose:
        raise RuntimeError("Validation purpose does not match this container")
    if (container.get("HostConfig") or {}).get("AutoRemove") is not True:
        raise RuntimeError("Disposable containers must be created with --rm")
    return container


def validate_tmpfs_options(options: str) -> None:
    """Require explicit writable memory storage capped at 512 MiB."""
    if not isinstance(options, str):
        raise RuntimeError("Invalid tmpfs options")
    parts = options.split(",")
    sizes = [part[5:] for part in parts if part.startswith("size=")]
    if len(parts) != len(set(parts)) or parts.count("rw") != 1 or len(sizes) != 1:
        raise RuntimeError("Expected writable tmpfs with one explicit size limit")
    if any(part not in {"rw", "noexec", "nosuid", "nodev"} and not part.startswith("size=") for part in parts):
        raise RuntimeError("Unexpected tmpfs options")
    size = re.fullmatch(r"([0-9]+)([kKmMgG]?)", sizes[0])
    if not size:
        raise RuntimeError("Invalid tmpfs size limit")
    multiplier = {"": 1, "k": 1024, "m": 1024**2, "g": 1024**3}[size[2].lower()]
    if not 0 < int(size[1]) * multiplier <= MAX_TMPFS_BYTES:
        raise RuntimeError("Tmpfs size must be positive and at most 512 MiB")


def validate_disposable_target(container_id: str, run_token: str, purpose: str) -> str:
    container = owned_container(container_id, run_token, purpose)
    if (container.get("State") or {}).get("Running") is not True:
        raise RuntimeError("Disposable validation container is not running")
    host = container.get("HostConfig") or {}
    mounts = container.get("Mounts") or []
    # --tmpfs uses HostConfig.Tmpfs; its legacy representation may have Mounts=[].
    # A mirrored tmpfs entry is also accepted, but no volume/bind/extra mount is.
    if not isinstance(mounts, list) or len(mounts) > 1:
        raise RuntimeError("Unexpected mounts; persistent mounts are prohibited")
    if mounts and (mounts[0].get("Type") != "tmpfs" or mounts[0].get("Destination") != DATA_DIRECTORY):
        raise RuntimeError("Expected only data-directory tmpfs; persistent mounts are prohibited")
    tmpfs = host.get("Tmpfs") or {}
    if not isinstance(tmpfs, dict) or set(tmpfs) != {DATA_DIRECTORY}:
        raise RuntimeError("Expected only the PostgreSQL data-directory tmpfs")
    validate_tmpfs_options(tmpfs[DATA_DIRECTORY])
    if host.get("Binds") or host.get("Mounts") or host.get("VolumesFrom"):
        raise RuntimeError("Unexpected bind, mount, or inherited storage configuration")
    data_directories = [entry.split("=", 1)[1] for entry in (container.get("Config") or {}).get("Env", []) if entry.startswith("PGDATA=")]
    if data_directories != [DATA_DIRECTORY]:
        raise RuntimeError("PostgreSQL data directory must be the validated tmpfs")
    if host.get("PortBindings") or host.get("PublishAllPorts"):
        raise RuntimeError("Database containers with published host ports are prohibited")
    if host.get("NetworkMode") != "none":
        raise RuntimeError("Disposable validation containers must use Docker network=none")
    return container_id


def validate_cleanup_target(container_id: str, run_token: str, purpose: str) -> str:
    # Ownership, not successful database validation, authorizes cleanup. A failed
    # bootstrap/misconfigured run-owned container still needs to be stopped.
    owned_container(container_id, run_token, purpose)
    return container_id


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["local", "validate", "cleanup"])
    parser.add_argument("target", nargs="*")
    args = parser.parse_args(argv)
    if args.action == "local":
        if args.target:
            parser.error("local accepts no target")
        validate_local_engine()
        print("LOCAL PASS")
    else:
        if len(args.target) != 3:
            parser.error("target requires full container ID, run token, and purpose")
        validator = validate_disposable_target if args.action == "validate" else validate_cleanup_target
        print(validator(*args.target))


if __name__ == "__main__":
    main()
