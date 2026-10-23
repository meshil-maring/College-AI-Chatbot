"""Safety regressions using mocked subprocesses only; no Docker/DB access."""

import os
import sys
import unittest
from unittest.mock import patch

import disposable_container as target
from container_fixtures import (
    CONTAINER_ID,
    RUN_TOKEN,
    PURPOSE,
    inspected_container,
    mock_commands,
)


class DisposableTargetTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ, {"DOCKER_HOST": "", "DOCKER_CONTEXT": ""}
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def call_with(self, container, *, cleanup=False, mode="valid", purpose=PURPOSE):
        calls = []
        validator = (
            target.validate_cleanup_target
            if cleanup
            else target.validate_disposable_target
        )
        with patch("subprocess.run", side_effect=mock_commands(container, calls, mode)):
            return validator(CONTAINER_ID, RUN_TOKEN, purpose)

    def test_accepts_exact_isolated_run_owned_container(self):
        self.assertEqual(self.call_with(inspected_container()), CONTAINER_ID)

    def test_rejects_wrong_run_token(self):
        value = inspected_container()
        value["Config"]["Labels"]["collegeai.validation.run"] = "c" * 32
        with self.assertRaisesRegex(RuntimeError, "Run token"):
            self.call_with(value)

    def test_rejects_persistent_volume(self):
        value = inspected_container()
        value["Mounts"] = [{"Type": "volume", "Destination": target.DATA_DIRECTORY}]
        with self.assertRaisesRegex(RuntimeError, "persistent mounts"):
            self.call_with(value)

    def test_rejects_published_port(self):
        value = inspected_container()
        value["HostConfig"]["PortBindings"] = {"5432/tcp": [{"HostPort": "54322"}]}
        with self.assertRaisesRegex(RuntimeError, "published host ports"):
            self.call_with(value)

    def test_rejects_network_access(self):
        value = inspected_container()
        value["HostConfig"]["NetworkMode"] = "bridge"
        with self.assertRaisesRegex(RuntimeError, "network=none"):
            self.call_with(value)

    def test_rejects_arbitrary_id_before_inspection(self):
        with patch("subprocess.run", side_effect=AssertionError("subprocess reached")):
            with self.assertRaisesRegex(RuntimeError, "64-character"):
                target.validate_disposable_target(
                    "supabase_db_CollegeAIChatbot", RUN_TOKEN, PURPOSE
                )

    def test_accepts_legacy_and_mirrored_tmpfs_metadata(self):
        for mounts in [[], [{"Type": "tmpfs", "Destination": target.DATA_DIRECTORY}]]:
            with self.subTest(mounts=mounts):
                value = inspected_container()
                value["Mounts"] = mounts
                self.assertEqual(self.call_with(value), CONTAINER_ID)

    def test_rejects_invalid_tmpfs_limits(self):
        cases = [
            "rw",
            "rw,size=0",
            "rw,size=-1",
            "rw,size=536870913",
            "rw,size=1g",
            "size=512m",
            "rw,size=bogus",
            "rw,size=1,size=2",
            "rw,rw,size=1",
            "rw,size=1,unknown",
            "rw,size=1,",
            None,
        ]
        for options in cases:
            with self.subTest(options=options):
                value = inspected_container()
                value["HostConfig"]["Tmpfs"][target.DATA_DIRECTORY] = options
                with self.assertRaises(RuntimeError):
                    self.call_with(value)

    def test_accepts_bounded_size_units(self):
        for options in [
            "rw,size=1",
            "rw,size=512m",
            "rw,size=524288k,nosuid,nodev,noexec",
        ]:
            value = inspected_container()
            value["HostConfig"]["Tmpfs"][target.DATA_DIRECTORY] = options
            self.assertEqual(self.call_with(value), CONTAINER_ID)

    def test_rejects_extra_or_alternative_storage(self):
        cases = {
            "binds": lambda c: c["HostConfig"].update(Binds=["/disk:/data"]),
            "raw_mount": lambda c: c["HostConfig"].update(Mounts=[{"Type": "volume"}]),
            "inherited": lambda c: c["HostConfig"].update(VolumesFrom=["other"]),
            "extra_tmpfs": lambda c: c["HostConfig"]["Tmpfs"].update(
                {"/extra": "rw,size=1"}
            ),
            "missing_tmpfs": lambda c: c["HostConfig"].update(Tmpfs={}),
            "bind_mount": lambda c: c.update(
                Mounts=[{"Type": "bind", "Destination": target.DATA_DIRECTORY}]
            ),
            "extra_mount": lambda c: c.update(
                Mounts=[
                    {"Type": "tmpfs", "Destination": target.DATA_DIRECTORY},
                    {"Type": "volume", "Destination": "/extra"},
                ]
            ),
            "wrong_destination": lambda c: c.update(
                Mounts=[{"Type": "tmpfs", "Destination": "/extra"}]
            ),
            "wrong_pgdata": lambda c: c["Config"].update(Env=["PGDATA=/other"]),
            "missing_pgdata": lambda c: c["Config"].update(Env=[]),
            "duplicate_pgdata": lambda c: c["Config"].update(
                Env=["PGDATA=/other", "PGDATA=" + target.DATA_DIRECTORY]
            ),
            "publish_all": lambda c: c["HostConfig"].update(PublishAllPorts=True),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                value = inspected_container()
                mutate(value)
                with self.assertRaises(RuntimeError):
                    self.call_with(value)

    def test_validation_and_cleanup_reject_foreign_ownership(self):
        cases = {
            "persistent_name": lambda c: c.update(Name="/supabase_db_CollegeAIChatbot"),
            "other_run_name": lambda c: c.update(
                Name="/codex-faculty-attendance-" + "c" * 12
            ),
            "different_id": lambda c: c.update(Id="c" * 64),
            "missing_labels": lambda c: c["Config"].update(Labels={}),
            "wrong_token": lambda c: c["Config"]["Labels"].update(
                {"collegeai.validation.run": "c" * 32}
            ),
            "wrong_purpose": lambda c: c["Config"]["Labels"].update(
                {"collegeai.validation.purpose": "academic-setup"}
            ),
            "wrong_image": lambda c: c["Config"].update(Image="postgres:latest"),
            "no_autoremove": lambda c: c["HostConfig"].update(AutoRemove=False),
        }
        for name, mutate in cases.items():
            for cleanup in [False, True]:
                with self.subTest(case=name, cleanup=cleanup):
                    value = inspected_container()
                    mutate(value)
                    with self.assertRaises(RuntimeError):
                        self.call_with(value, cleanup=cleanup)

    def test_cleanup_accepts_owned_failed_bootstrap_without_sql_or_templates(self):
        value = inspected_container()
        value["State"]["Running"] = False
        value["Mounts"] = [{"Type": "volume", "Destination": target.DATA_DIRECTORY}]
        calls = []
        with patch("subprocess.run", side_effect=mock_commands(value, calls)):
            self.assertEqual(
                target.validate_cleanup_target(CONTAINER_ID, RUN_TOKEN, PURPOSE),
                CONTAINER_ID,
            )
        self.assertIn(target.docker_arguments("inspect", CONTAINER_ID), calls)
        self.assertFalse(any("{{ index" in str(arg) for call in calls for arg in call))
        self.assertFalse(any("exec" in call or "stop" in call for call in calls))

    def test_rejects_stopped_container_for_database_operations(self):
        value = inspected_container()
        value["State"]["Running"] = False
        with self.assertRaisesRegex(RuntimeError, "not running"):
            self.call_with(value)

    def test_remote_or_unavailable_engine_and_inspect_fail_closed(self):
        for mode in [
            "remote_context",
            "remote_endpoint",
            "wrong_engine",
            "inspect_failed",
            "malformed_json",
        ]:
            with self.subTest(mode=mode):
                with self.assertRaises((RuntimeError, ValueError)):
                    self.call_with(inspected_container(), mode=mode)

    def test_rejects_docker_environment_overrides(self):
        for name in ["DOCKER_HOST", "DOCKER_CONTEXT"]:
            with (
                self.subTest(variable=name),
                patch.dict(os.environ, {name: "remote"}),
                patch(
                    "subprocess.run", side_effect=AssertionError("subprocess reached")
                ),
            ):
                with self.assertRaises(RuntimeError):
                    target.validate_local_engine()


if __name__ == "__main__":
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
