"""Synthetic fixtures; reject accidental live subprocess or socket access."""
from copy import deepcopy
import json
from subprocess import CompletedProcess, TimeoutExpired
import unittest
from unittest.mock import patch

from ..policy import (
    DATA_DIRECTORY, ENTRYPOINT, EXPECTED_IMAGE, START_COMMAND, Pins,
    labels_for, name_for,
)
from ..session import Session
from ..transport import Docker
from ..identity import config_digest

IMAGE = "sha256:" + "1" * 64
CONTAINER = "2" * 64
IMAGE_CONFIG = {"Volumes": {DATA_DIRECTORY: {}}, "User": "postgres",
                "Entrypoint": ["/synthetic/image-entrypoint"], "Cmd": ["postgres"]}
PINS = Pins(IMAGE, "local-engine-123456789", "C:/Docker/bin/docker.exe", 999, 999,
            "27.1.1", "27.1.1", "a" * 64, config_digest(IMAGE_CONFIG), config_digest(START_COMMAND))


def container_metadata(token):
    return {
        "Id": CONTAINER, "Name": "/" + name_for(token), "Image": IMAGE,
        "Config": {
            "Image": IMAGE, "Labels": labels_for(token), "User": PINS.user,
            "Env": [f"PGDATA={DATA_DIRECTORY}"], "Volumes": {DATA_DIRECTORY: {}},
            "Entrypoint": deepcopy(ENTRYPOINT), "Cmd": deepcopy(START_COMMAND),
        },
        "State": {"Running": False, "Paused": False, "Restarting": False, "Status": "created"},
        "Mounts": [],
        "NetworkSettings": {"Ports": {}, "Networks": {}},
        "HostConfig": {
            "AutoRemove": True, "NetworkMode": "none", "PublishAllPorts": False,
            "PortBindings": {}, "Tmpfs": {DATA_DIRECTORY: PINS.tmpfs},
            "Binds": None, "Mounts": None, "VolumesFrom": None,
            "Devices": [], "DeviceRequests": None, "DeviceCgroupRules": None,
            "CapAdd": None, "CapDrop": ["ALL"], "Privileged": False,
            "ReadonlyRootfs": True, "SecurityOpt": ["no-new-privileges:true"],
            "PidMode": "", "IpcMode": "private", "UTSMode": "",
            "CgroupnsMode": "private", "UsernsMode": "",
        },
    }


class FakeTransport:
    def __init__(self):
        self.calls = []
        self.engine = {"ID": PINS.engine_id, "Name": "docker-desktop",
                       "OSType": "linux", "Architecture": "x86_64"}
        self.image = {"Id": IMAGE, "RepoTags": [EXPECTED_IMAGE], "Os": "linux",
                      "Architecture": "amd64", "Config": deepcopy(IMAGE_CONFIG)}
        self.version = {"Client": {"Version": PINS.docker_client_version},
                        "Server": {"Version": PINS.docker_server_version}}
        self.runtime_identity = ("999\n999\n999:999:999:999\n999:999:999:999\n"
                                 "postgres (PostgreSQL) 17.6\ninitdb (PostgreSQL) 17.6\n")
        self.removed = False
        self.removal_confirmed = True
        self.container = None
        self.session = None
        self.timeout = None
        self.fail = None
        self.sql_results = []
        self.ready_code = 0

    def __call__(self, arguments, *, input=None, timeout=20):
        assert arguments[:3] == [PINS.docker_executable, "--host", PINS.endpoint]
        operation = arguments[3:]
        self.calls.append((operation, input, timeout))
        if operation[0] == self.timeout:
            raise TimeoutExpired(arguments, timeout, output="secret-output", stderr="secret-error")
        if operation[0] == self.fail:
            return CompletedProcess(arguments, 1, "secret-output", "secret-error")
        if operation[0] == "version":
            output = json.dumps(self.version)
        elif operation[0] == "info":
            output = json.dumps(self.engine)
        elif operation[:2] == ["image", "inspect"]:
            output = json.dumps([self.image])
        elif operation[:2] == ["container", "inspect"]:
            assert operation[2] == CONTAINER
            output = json.dumps([self.container])
        elif operation[:2] == ["container", "ls"]:
            assert operation[4:6] == ["--filter", f"id={CONTAINER}"]
            output = "" if self.removed and self.removal_confirmed else CONTAINER + "\n"
        elif operation[0] == "create":
            self.container = container_metadata(self.session.token)
            self.container["Config"]["Labels"] = (self.image["Config"].get("Labels") or {}) | labels_for(self.session.token)
            output = CONTAINER
        elif operation == ["start", CONTAINER]:
            self.container["State"].update(Running=True, Status="running")
            self.container["NetworkSettings"]["Networks"] = {"none": {}}
            output = CONTAINER
        elif operation[0] == "exec":
            assert CONTAINER in operation
            if operation[-1] == "1":
                return CompletedProcess(arguments, self.ready_code, "", "")
            if "-ceu" in operation:
                return CompletedProcess(arguments, 0, self.runtime_identity, "")
            if self.sql_results:
                code, stdout, stderr = self.sql_results.pop(0)
                return CompletedProcess(arguments, code, stdout, stderr)
            output = ""
        elif operation[0] in {"stop", "rm"}:
            assert operation[-1] == CONTAINER
            output = CONTAINER
            self.removed = True
        else:
            raise AssertionError("Unexpected mocked operation")
        return CompletedProcess(arguments, 0, output, "")


class OfflineCase(unittest.TestCase):
    def setUp(self):
        for target in ("subprocess.run", "subprocess.Popen", "socket.create_connection",
                       "socket.socket.connect", "socket.socket.connect_ex", "socket.getaddrinfo"):
            blocker = patch(target, side_effect=AssertionError("Live I/O is forbidden in unit tests"))
            blocker.start()
            self.addCleanup(blocker.stop)

    def session(self, *, created=True, started=False):
        fake = FakeTransport()
        session = Session(Docker(PINS, fake))
        fake.session = session
        if created:
            session.create()
        if started:
            session.start()
        return session, fake

    def mutating_operations(self, fake):
        return [call[0][0] for call in fake.calls
                if call[0][0] in {"start", "stop", "rm", "exec"}]
