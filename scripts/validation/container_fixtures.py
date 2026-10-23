"""Synthetic Docker metadata and subprocess doubles for container safety tests."""

import json

import disposable_container as target

CONTAINER_ID = "a" * 64


RUN_TOKEN = "b" * 32


PURPOSE = "faculty-attendance"


def inspected_container(purpose=PURPOSE, token=RUN_TOKEN):
    return {
        "Id": CONTAINER_ID,
        "Name": "/" + target.expected_name(token, purpose),
        "State": {"Running": True},
        "Config": {
            "Image": target.EXPECTED_IMAGE,
            "Env": ["PGDATA=" + target.DATA_DIRECTORY],
            "Labels": {
                "collegeai.validation.disposable": "true",
                "collegeai.validation.run": token,
                "collegeai.validation.purpose": purpose,
            },
        },
        "Mounts": [],
        "HostConfig": {
            "Binds": [],
            "Mounts": [],
            "VolumesFrom": [],
            "Tmpfs": {target.DATA_DIRECTORY: "rw,size=536870912"},
            "AutoRemove": True,
            "PortBindings": {},
            "PublishAllPorts": False,
            "NetworkMode": "none",
        },
    }


def mock_commands(container, calls, mode="valid"):
    def run(argv, **kwargs):
        calls.append(argv)
        pinned = ["docker", "--context", "desktop-linux"]
        if argv == ["docker", "context", "show"]:
            output = "remote" if mode == "remote_context" else "desktop-linux"
        elif argv == pinned + ["context", "inspect", "desktop-linux"]:
            endpoint = (
                "tcp://example.invalid:2375"
                if mode == "remote_endpoint"
                else target.LOCAL_ENDPOINT
            )
            output = json.dumps([{"Endpoints": {"docker": {"Host": endpoint}}}])
        elif argv == pinned + ["info", "--format", "{{.Name}} {{.OSType}}"]:
            output = (
                "remote-engine linux"
                if mode == "wrong_engine"
                else "docker-desktop linux"
            )
        elif argv == pinned + ["inspect", CONTAINER_ID]:
            if mode == "inspect_failed":
                from subprocess import CompletedProcess

                return CompletedProcess(argv, 1, "", "inspection unavailable")
            output = "not json" if mode == "malformed_json" else json.dumps([container])
        else:
            raise AssertionError("Unmocked Docker/database operation: " + repr(argv))
        from subprocess import CompletedProcess

        return CompletedProcess(argv, 0, output + "\n", "")

    return run
