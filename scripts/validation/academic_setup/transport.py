"""Bounded Docker transport. Live invocation is sealed during preparation."""
import json
import os
import subprocess
import tempfile

from . import policy
from .policy import HarnessError, require
from .identity import config_digest, validate_bootstrap, validate_executable, validate_versions


class LiveTransport:
    def __call__(self, arguments, *, input=None, timeout=20,
                 checkpoint=lambda: None, budget=None):
        require(policy.EXECUTION_AUTHORIZED,
                "Stage 4B-5 permits offline review only; live execution is disabled")
        # Private Docker config and a small OS-only environment prevent credentials,
        # contexts, proxies, DOCKER_* and PG* settings from reaching the child.
        with tempfile.TemporaryDirectory(prefix="academic-docker-") as directory:
            environment = {"TEMP": directory, "TMP": directory}
            for key in ("SystemRoot", "WINDIR"):
                if key in os.environ:
                    environment[key] = os.environ[key]
            checkpoint()
            if budget is not None:
                timeout = min(timeout, budget())
                require(timeout > 0, "Operation deadline exceeded")
            # Process creation may outlast timeout. A late completion is refused;
            # killing the client never establishes database-side cancellation.
            result = subprocess.run(
                [arguments[0], "--config", directory, *arguments[1:]],
                input=input, capture_output=True, text=True, encoding="utf-8",
                timeout=timeout, check=False, env=environment, cwd=directory,
                shell=False,
            )
            checkpoint()
            return result


class Docker:
    def __init__(self, pins, transport=None):
        pins.validate()
        self.pins = pins
        self.transport = transport if transport is not None else LiveTransport()
        self.image_labels = {}

    def call(self, *arguments, sql=None, timeout=20, allow_failure=False,
             checkpoint=lambda: None, budget=None):
        require(type(timeout) in (int, float) and 0 < timeout <= 120,
                "Invalid operation timeout")
        command = [self.pins.docker_executable, "--host", self.pins.endpoint, *arguments]
        try:
            if isinstance(self.transport, LiveTransport):
                require(policy.EXECUTION_AUTHORIZED, "offline review only; live execution is disabled")
                validate_executable(self.pins)
            checkpoint()
            if budget is not None:
                timeout = min(timeout, budget())
                require(timeout > 0, "Operation deadline exceeded")
            if isinstance(self.transport, LiveTransport):
                result = self.transport(command, input=sql, timeout=timeout,
                                        checkpoint=checkpoint, budget=budget)
            else:
                result = self.transport(command, input=sql, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise HarnessError("Docker operation timed out; outcome is unverified") from None
        except (OSError, UnicodeError):
            raise HarnessError("Docker operation unavailable") from None
        checkpoint()
        require(type(result.returncode) is int, "Invalid Docker completion")
        if not allow_failure:
            require(result.returncode == 0, "Docker operation failed")
        return result

    def object(self, *arguments, singleton=False, checkpoint=lambda: None, budget=None):
        result = self.call(*arguments, checkpoint=checkpoint, budget=budget)
        checkpoint()
        try:
            value = json.loads(result.stdout)
        except (ValueError, TypeError):
            raise HarnessError("Invalid Docker inspection response") from None
        if singleton:
            require(isinstance(value, list) and len(value) == 1,
                    "Expected one Docker inspection object")
            value = value[0]
        require(isinstance(value, dict), "Invalid Docker inspection object")
        return value

    def preflight(self, checkpoint=lambda: None, budget=None):
        validate_bootstrap(self.pins)
        validate_versions(self.object("version", "--format", "{{json .}}",
                                      checkpoint=checkpoint, budget=budget), self.pins)
        engine = self.object("info", "--format", "{{json .}}", checkpoint=checkpoint, budget=budget)
        require(engine.get("ID") == self.pins.engine_id
                and engine.get("Name") == "docker-desktop"
                and engine.get("OSType") == "linux"
                and engine.get("Architecture") in ("x86_64", "amd64"),
                "Wrong Docker engine identity or platform")
        image = self.object("image", "inspect", policy.EXPECTED_IMAGE,
                            singleton=True, checkpoint=checkpoint, budget=budget)
        require(image.get("Id") == self.pins.image_id
                and isinstance(image.get("RepoTags"), list)
                and policy.EXPECTED_IMAGE in image["RepoTags"]
                and image.get("Os") == "linux" and image.get("Architecture") == "amd64",
                "Wrong PostgreSQL image identity or platform")
        configuration = image.get("Config")
        require(isinstance(configuration, dict) and "Volumes" in configuration,
                "Missing image configuration")
        require(config_digest(configuration) == self.pins.image_config_sha256,
                "Image bootstrap configuration has not been reviewed")
        volumes = configuration.get("Volumes")
        require(volumes is None or (isinstance(volumes, dict)
                and set(volumes) <= {policy.DATA_DIRECTORY}),
                "Image declares unexpected persistent storage")
        labels = configuration.get("Labels") or {}
        require(isinstance(labels, dict) and all(isinstance(key, str) and isinstance(value, str)
                for key, value in labels.items()), "Invalid image labels")
        self.image_labels = labels
        return engine, image
