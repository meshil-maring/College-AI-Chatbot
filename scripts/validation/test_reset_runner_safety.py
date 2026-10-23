"""Mocked cleanup regressions for the historical account reset runner."""

import contextlib
import importlib
import io
import unittest
from unittest.mock import patch

import disposable_container as target
from container_fixtures import CONTAINER_ID, inspected_container, mock_commands


class ResetRunnerSafetyTests(unittest.TestCase):
    def test_reset_runner_rejects_persistent_target_without_probe_or_sql(self):
        reset = importlib.import_module("verify_supabase_data_reset")
        calls = []

        def reject_persistent(argv, **kwargs):
            if argv[3:4] == ["run"]:
                from subprocess import CompletedProcess

                return CompletedProcess(argv, 0, "supabase_db_CollegeAIChatbot", "")
            return mock_commands(inspected_container(), calls)(argv, **kwargs)

        with (
            patch("subprocess.run", side_effect=reject_persistent),
            self.assertRaisesRegex(RuntimeError, "valid ID"),
        ):
            reset.main()
        self.assertFalse(any("exec" in call or "stop" in call for call in calls))

    def reset_scenario(self, scenario):
        reset = importlib.import_module("verify_supabase_data_reset")
        container = inspected_container(purpose="data-reset")
        calls = []

        def run(argv, **kwargs):
            from subprocess import CompletedProcess

            operation = (
                argv[3]
                if argv[:3] == ["docker", "--context", "desktop-linux"]
                else None
            )
            if operation == "run":
                calls.append(argv)
                token = next(
                    arg.split("=", 1)[1]
                    for arg in argv
                    if arg.startswith("collegeai.validation.run=")
                )
                container["Name"] = "/" + target.expected_name(token, "data-reset")
                container["Config"]["Labels"]["collegeai.validation.run"] = token
                if scenario == "foreign":
                    container["Name"] = "/supabase_db_CollegeAIChatbot"
                if scenario == "volume":
                    container["Mounts"] = [
                        {"Type": "volume", "Destination": target.DATA_DIRECTORY}
                    ]
                return CompletedProcess(
                    argv,
                    1 if scenario == "creation_failed" else 0,
                    CONTAINER_ID,
                    "creation failed",
                )
            if operation == "exec":
                calls.append(argv)
                if scenario != "bootstrap_failed" or argv[5] != "cat":
                    raise AssertionError("Database operation reached: " + repr(argv))
                raise RuntimeError("mock bootstrap failure")
            if operation == "stop":
                calls.append(argv)
                return CompletedProcess(argv, 0, CONTAINER_ID, "")
            return mock_commands(container, calls)(argv, **kwargs)

        with (
            contextlib.redirect_stdout(io.StringIO()),
            patch("subprocess.run", side_effect=run),
            self.assertRaises(RuntimeError),
        ):
            reset.main()
        return calls

    def test_reset_full_id_persistent_storage_rejected_and_owned_failure_cleaned(self):
        calls = self.reset_scenario("volume")
        self.assertFalse(any("exec" in call for call in calls))
        self.assertEqual(
            [call for call in calls if "stop" in call],
            [target.docker_arguments("stop", "--timeout", "10", CONTAINER_ID)],
        )

    def test_reset_foreign_full_id_never_probed_or_stopped(self):
        calls = self.reset_scenario("foreign")
        self.assertFalse(any("exec" in call or "stop" in call for call in calls))

    def test_reset_creation_failure_never_cleans_borrowed_id(self):
        calls = self.reset_scenario("creation_failed")
        self.assertFalse(
            any(
                "exec" in call or "inspect" in call[3:4] or "stop" in call
                for call in calls
            )
        )

    def test_reset_bootstrap_failure_cleans_only_validated_created_id(self):
        calls = self.reset_scenario("bootstrap_failed")
        probe = next(i for i, call in enumerate(calls) if "exec" in call)
        inspect = next(i for i, call in enumerate(calls) if call[3:4] == ["inspect"])
        self.assertLess(inspect, probe)
        self.assertEqual(
            [call for call in calls if "stop" in call],
            [target.docker_arguments("stop", "--timeout", "10", CONTAINER_ID)],
        )
