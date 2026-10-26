"""Future lifecycle API; default transport refuses all live execution in Stage 4B-5."""
import re
import secrets
import time

from .metadata import validate_container
from .identity import RUNTIME_IDENTITY_COMMAND
from .policy import (
    BINARY_DIRECTORY, DATA_DIRECTORY, ENTRYPOINT, START_COMMAND, HarnessError,
    labels_for, name_for, require, validate_identity,
)


class Session:
    def __init__(self, docker):
        self.docker = docker
        self.token = secrets.token_hex(16)
        self.container_id = None
        self.failed = False
        self.closed = False
        self.create_attempted = False
        self.create_submitted = False
        self.readiness_pending = False

    def create(self):
        require(not self.create_attempted and not self.closed, "Session cannot be reused")
        self.create_attempted = True
        try:
            self.docker.preflight()
            pins = self.docker.pins
            arguments = [
                "create", "--pull=never", "--rm", "--network", "none",
                "--read-only", "--cap-drop", "ALL", "--security-opt",
                "no-new-privileges:true", "--ipc", "private", "--cgroupns", "private",
                "--user", pins.user, "--name", name_for(self.token),
                "--tmpfs", f"{DATA_DIRECTORY}:{pins.tmpfs}",
                "--env", f"PGDATA={DATA_DIRECTORY}", "--entrypoint", ENTRYPOINT[0],
            ]
            for key, value in labels_for(self.token).items():
                arguments.extend(["--label", f"{key}={value}"])
            self.create_submitted = True
            result = self.docker.call(*arguments, pins.image_id, *START_COMMAND)
            container_id = result.stdout.strip()
            validate_identity(container_id, self.token)
            self.container_id = container_id
            self.inspect(running=False)
            return container_id
        except HarnessError:
            self.failed = True
            raise

    def inspect(self, *, running=None, checkpoint=lambda: None, budget=None):
        require(self.container_id is not None and not self.closed,
                "No acknowledged full container ID")
        validate_identity(self.container_id, self.token)
        self.docker.preflight(checkpoint=checkpoint, budget=budget)
        container = self.docker.object("container", "inspect", self.container_id,
                                       singleton=True, checkpoint=checkpoint, budget=budget)
        return validate_container(container, self.container_id, self.token,
                                  self.docker.pins, running=running,
                                  image_labels=self.docker.image_labels)

    def start(self):
        require(not self.failed, "Session has failed")
        try:
            self.inspect(running=False)
            self.docker.call("start", self.container_id)
            self.inspect(running=True)
        except HarnessError:
            self.failed = True
            raise

    def exec_arguments(self, binary, *arguments, interactive=False):
        return [
            "exec", *(["-i"] if interactive else []), "--user", self.docker.pins.user,
            self.container_id, "/usr/bin/env", "-i",
            f"PATH={BINARY_DIRECTORY}:/usr/bin:/bin", f"PGDATA={DATA_DIRECTORY}",
            f"{BINARY_DIRECTORY}/{binary}", *arguments,
        ]

    def ready(self, *, timeout=60, clock=time.monotonic, sleep=time.sleep):
        require(not self.failed, "Session has failed")
        require(type(timeout) in (int, float) and 0 < timeout <= 60,
                "Invalid readiness timeout")
        deadline = clock() + timeout
        budget = lambda: deadline-clock()
        self.readiness_pending = True
        def checkpoint():
            require(clock() < deadline, "Database readiness deadline exceeded")
        try:
            while True:
                checkpoint()
                self.inspect(running=True, checkpoint=checkpoint, budget=budget)
                checkpoint()
                result = self.docker.call(
                    *self.exec_arguments("pg_isready", "-h", DATA_DIRECTORY,
                                         "-U", "postgres", "-d", "postgres", "-t", "1"),
                    timeout=5, allow_failure=True, checkpoint=checkpoint, budget=budget,
                )
                checkpoint()
                if result.returncode == 0:
                    self.runtime_identity(checkpoint, budget=budget)
                    checkpoint()
                    self.readiness_pending = False
                    return
                require(result.returncode in (1, 2), "Database readiness check failed")
                sleep(min(0.1, max(0, budget())))
        except HarnessError:
            self.failed = True
            raise

    def runtime_identity(self, checkpoint, *, budget=None):
        pins = self.docker.pins
        result = self.docker.call(
            "exec", "--user", pins.user, self.container_id, "/usr/bin/env", "-i",
            "/bin/sh", "-ceu", RUNTIME_IDENTITY_COMMAND,
            timeout=5, checkpoint=checkpoint, budget=budget,
        )
        checkpoint()
        require(result.stdout.splitlines() == [str(pins.postgres_uid), str(pins.postgres_gid),
                ":".join([str(pins.postgres_uid)]*4), ":".join([str(pins.postgres_gid)]*4),
                "postgres (PostgreSQL) 17.6", "initdb (PostgreSQL) 17.6"],
                "PostgreSQL runtime identity or bootstrap binaries differ")

    def sql(self, text, *, expected_sqlstate=None, expected_message=None, clock=time.monotonic):
        require(not self.failed, "Session has failed")
        require(not self.readiness_pending, "Readiness is unverified")
        deadline = clock() + 120
        budget = lambda: deadline-clock()
        def checkpoint():
            require(clock() < deadline, "SQL inspection deadline exceeded")
        if expected_sqlstate is not None:
            require(re.fullmatch(r"[0-9A-Z]{5}", expected_sqlstate), "Invalid SQLSTATE")
        try:
            self.inspect(running=True, checkpoint=checkpoint, budget=budget)
            self.runtime_identity(checkpoint, budget=budget)
            checkpoint()
            remaining = deadline-clock()
            require(remaining > 0, "SQL inspection deadline exceeded")
            result = self.docker.call(
                *self.exec_arguments(
                    "psql", "-X", "--no-password", "-h", DATA_DIRECTORY, "-U", "postgres",
                    "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=verbose",
                    "-qAt", "-f", "-", interactive=True,
                ), sql=text, timeout=remaining, allow_failure=True,
                checkpoint=checkpoint, budget=budget,
            )
            checkpoint()
            if expected_sqlstate:
                # This harness always uses `psql -f -`: only its stdin location
                # prefix is legitimate. Never consume arbitrary colon content.
                error_lines = result.stderr.replace("\r\n", "\n").split("\n")
                pattern = r"(?:psql:<stdin>:[1-9][0-9]*:[ \t]+)?ERROR:[ \t]+([0-9A-Z]{5})(?::[ \t]+([^\r\n]*))?"
                errors = [re.fullmatch(pattern, line) for line in error_lines]
                errors = [match for match in errors if match is not None]
                diagnostic = r"psql:<stdin>:[1-9][0-9]*:[ \t]+(?:NOTICE|WARNING|INFO|LOG|DEBUG[1-5]):[^\r\n]*"
                ambiguous = any(line.startswith(("ERROR:", "psql:"))
                                and re.fullmatch(pattern, line) is None
                                and re.fullmatch(diagnostic, line) is None for line in error_lines)
                require(result.returncode == 3 and not ambiguous and len(errors) == 1
                        and errors[0][1] == expected_sqlstate,
                    "Expected rollback probe did not produce its reviewed SQLSTATE")
                if expected_message is not None:
                    require(errors[0][2] == expected_message,
                            "Expected prerequisite rejection message missing")
            else:
                require(result.returncode == 0, "SQL verification failed; replay stopped")
            return result.stdout
        except HarnessError:
            self.failed = True
            raise

    def cleanup(self):
        # Full isolation checks apply even after failed SQL/startup. If any field
        # differs, leave the target untouched and require manual review.
        if self.container_id is None:
            require(not self.create_submitted, "Create outcome unverified; manual review required")
            self.closed = True
            return
        container = self.inspect()
        if container["State"]["Running"]:
            self.docker.call("stop", "--time", "10", self.container_id, timeout=20)
        else:
            self.docker.call("rm", self.container_id)
        self.docker.preflight()
        result = self.docker.call("container", "ls", "--all", "--no-trunc",
                                  "--filter", f"id={self.container_id}", "--format", "{{.ID}}")
        require(result.stdout == "", "Exact container removal unverified; manual review required")
        self.closed = True
