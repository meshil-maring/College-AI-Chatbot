"""Fixed Academic Setup isolation policy, independent of application settings."""
from dataclasses import dataclass
import re

from ..disposable_container import (
    DATA_DIRECTORY, EXPECTED_IMAGE, LOCAL_ENDPOINT, MAX_TMPFS_BYTES,
    validate_arguments, validate_tmpfs_options,
)

PURPOSE = "academic-setup"
HARNESS = "academic-setup-stage4b"
EXECUTION_AUTHORIZED = False
BINARY_DIRECTORY = "/usr/lib/postgresql/17/bin"
BASE_TMPFS = f"rw,noexec,nosuid,nodev,size={MAX_TMPFS_BYTES}"
STARTUP = (
    "umask 077; "
    f"{BINARY_DIRECTORY}/initdb -D {DATA_DIRECTORY} --username=postgres "
    "--auth-local=trust --auth-host=reject --encoding=UTF8 --locale=C >/dev/null; "
    f"exec {BINARY_DIRECTORY}/postgres -D {DATA_DIRECTORY} "
    "-c listen_addresses= "
    f"-c unix_socket_directories={DATA_DIRECTORY} "
    "-c unix_socket_permissions=0700 -c timezone=UTC -c shared_preload_libraries="
)
ENTRYPOINT = ["/usr/bin/env"]
START_COMMAND = [
    "-i", f"PATH={BINARY_DIRECTORY}:/usr/bin:/bin", f"PGDATA={DATA_DIRECTORY}",
    "/bin/sh", "-ceu", STARTUP,
]


class HarnessError(RuntimeError):
    """Sanitized failure: never contains command output, SQL or environment data."""


def require(condition, message):
    if not condition:
        raise HarnessError(message)


@dataclass(frozen=True)
class Pins:
    image_id: str
    engine_id: str
    docker_executable: str
    postgres_uid: int
    postgres_gid: int
    docker_client_version: str = ""
    docker_server_version: str = ""
    executable_sha256: str = ""
    image_config_sha256: str = ""
    bootstrap_sha256: str = ""
    endpoint: str = LOCAL_ENDPOINT

    def validate(self):
        require(self.endpoint == LOCAL_ENDPOINT, "Wrong Docker endpoint")
        require(isinstance(self.image_id, str)
                and re.fullmatch(r"sha256:[a-f0-9]{64}", self.image_id),
                "A full approved immutable image ID is required")
        require(isinstance(self.engine_id, str)
                and re.fullmatch(r"[A-Za-z0-9:_-]{16,128}", self.engine_id),
                "An approved engine ID is required")
        require(isinstance(self.docker_executable, str)
                and re.fullmatch(r"[A-Za-z]:/[A-Za-z0-9 /_.()-]+/docker[.]exe",
                                 self.docker_executable)
                and ".." not in self.docker_executable.split("/"),
                "An absolute local Docker executable path is required")
        for value in (self.postgres_uid, self.postgres_gid):
            require(type(value) is int and 0 < value < 65536,
                    "Reviewed non-root PostgreSQL UID/GID are required")
        for value in (self.docker_client_version, self.docker_server_version):
            require(isinstance(value, str) and re.fullmatch(r"[0-9]+[.][0-9]+[.][0-9]+", value),
                    "Reviewed Docker client/server versions are required")
        for value in (self.executable_sha256, self.image_config_sha256, self.bootstrap_sha256):
            require(isinstance(value, str) and re.fullmatch(r"[a-f0-9]{64}", value),
                    "Reviewed executable, image config and bootstrap fingerprints required")

    @property
    def user(self):
        return f"{self.postgres_uid}:{self.postgres_gid}"

    @property
    def tmpfs(self):
        validate_tmpfs_options(BASE_TMPFS)
        return (f"{BASE_TMPFS},uid={self.postgres_uid},"
                f"gid={self.postgres_gid},mode=0700")


def name_for(token):
    return f"codex-academic-setup-{token}"


def labels_for(token):
    return {
        "collegeai.validation.disposable": "true",
        "collegeai.validation.run": token,
        "collegeai.validation.purpose": PURPOSE,
        "collegeai.validation.harness": HARNESS,
    }


def validate_identity(container_id, token):
    try:
        validate_arguments(container_id, token, PURPOSE)
    except RuntimeError:
        raise HarnessError("Full container ID and valid run token required") from None
