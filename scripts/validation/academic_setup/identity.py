"""Offline-comparable identity evidence. No identity is inferred from a tag."""
from hashlib import sha256
import json
from pathlib import Path
import stat

from .policy import START_COMMAND, require
from .policy import BINARY_DIRECTORY

RUNTIME_IDENTITY_COMMAND = (
    "/usr/bin/id -u; /usr/bin/id -g; "
    "while read -r key a b c d rest; do case $key in Uid:|Gid:) "
    "printf '%s:%s:%s:%s\\n' \"$a\" \"$b\" \"$c\" \"$d\";; esac; done </proc/1/status; "
    f"{BINARY_DIRECTORY}/postgres --version; {BINARY_DIRECTORY}/initdb --version"
)


def config_digest(configuration):
    return sha256(json.dumps(configuration, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_bootstrap(pins):
    require(pins.bootstrap_sha256 == config_digest(START_COMMAND),
            "Bootstrap command has not been reviewed")


def validate_executable(pins):
    """Future live adapter checks every path component and the executable bytes."""
    path = Path(pins.docker_executable)
    for item in (*reversed(path.parents), path):
        metadata = item.lstat()
        require(not stat.S_ISLNK(metadata.st_mode)
                and not getattr(metadata, "st_file_attributes", 0) & 1024,
                "Linked Docker executable paths are prohibited")
    require(path.is_file() and sha256(path.read_bytes()).hexdigest() == pins.executable_sha256,
            "Docker executable fingerprint changed")


def validate_versions(value, pins):
    for key, version in (("Client", pins.docker_client_version),
                         ("Server", pins.docker_server_version)):
        component = value.get(key)
        require(isinstance(component, dict) and component.get("Version") == version,
                "Wrong Docker executable or engine version")
