"""Safety regressions using mocked subprocesses only; no Docker/DB access."""
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

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
            "Binds": [], "Mounts": [], "VolumesFrom": [],
            "Tmpfs": {target.DATA_DIRECTORY: "rw,size=536870912"},
            "AutoRemove": True, "PortBindings": {}, "PublishAllPorts": False,
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
            endpoint = "tcp://example.invalid:2375" if mode == "remote_endpoint" else target.LOCAL_ENDPOINT
            output = json.dumps([{"Endpoints": {"docker": {"Host": endpoint}}}])
        elif argv == pinned + ["info", "--format", "{{.Name}} {{.OSType}}"]:
            output = "remote-engine linux" if mode == "wrong_engine" else "docker-desktop linux"
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


class DisposableTargetTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"DOCKER_HOST": "", "DOCKER_CONTEXT": ""})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def call_with(self, container, *, cleanup=False, mode="valid", purpose=PURPOSE):
        calls = []
        validator = target.validate_cleanup_target if cleanup else target.validate_disposable_target
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
                target.validate_disposable_target("supabase_db_CollegeAIChatbot", RUN_TOKEN, PURPOSE)

    def test_accepts_legacy_and_mirrored_tmpfs_metadata(self):
        for mounts in [[], [{"Type": "tmpfs", "Destination": target.DATA_DIRECTORY}]]:
            with self.subTest(mounts=mounts):
                value = inspected_container()
                value["Mounts"] = mounts
                self.assertEqual(self.call_with(value), CONTAINER_ID)

    def test_rejects_invalid_tmpfs_limits(self):
        cases = ["rw", "rw,size=0", "rw,size=-1", "rw,size=536870913", "rw,size=1g",
                 "size=512m", "rw,size=bogus", "rw,size=1,size=2", "rw,rw,size=1",
                 "rw,size=1,unknown", "rw,size=1,", None]
        for options in cases:
            with self.subTest(options=options):
                value = inspected_container()
                value["HostConfig"]["Tmpfs"][target.DATA_DIRECTORY] = options
                with self.assertRaises(RuntimeError):
                    self.call_with(value)

    def test_accepts_bounded_size_units(self):
        for options in ["rw,size=1", "rw,size=512m", "rw,size=524288k,nosuid,nodev,noexec"]:
            value = inspected_container()
            value["HostConfig"]["Tmpfs"][target.DATA_DIRECTORY] = options
            self.assertEqual(self.call_with(value), CONTAINER_ID)

    def test_rejects_extra_or_alternative_storage(self):
        cases = {
            "binds": lambda c: c["HostConfig"].update(Binds=["/disk:/data"]),
            "raw_mount": lambda c: c["HostConfig"].update(Mounts=[{"Type": "volume"}]),
            "inherited": lambda c: c["HostConfig"].update(VolumesFrom=["other"]),
            "extra_tmpfs": lambda c: c["HostConfig"]["Tmpfs"].update({"/extra": "rw,size=1"}),
            "missing_tmpfs": lambda c: c["HostConfig"].update(Tmpfs={}),
            "bind_mount": lambda c: c.update(Mounts=[{"Type": "bind", "Destination": target.DATA_DIRECTORY}]),
            "extra_mount": lambda c: c.update(Mounts=[{"Type": "tmpfs", "Destination": target.DATA_DIRECTORY}, {"Type": "volume", "Destination": "/extra"}]),
            "wrong_destination": lambda c: c.update(Mounts=[{"Type": "tmpfs", "Destination": "/extra"}]),
            "wrong_pgdata": lambda c: c["Config"].update(Env=["PGDATA=/other"]),
            "missing_pgdata": lambda c: c["Config"].update(Env=[]),
            "duplicate_pgdata": lambda c: c["Config"].update(Env=["PGDATA=/other", "PGDATA=" + target.DATA_DIRECTORY]),
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
            "other_run_name": lambda c: c.update(Name="/codex-faculty-attendance-" + "c" * 12),
            "different_id": lambda c: c.update(Id="c" * 64),
            "missing_labels": lambda c: c["Config"].update(Labels={}),
            "wrong_token": lambda c: c["Config"]["Labels"].update({"collegeai.validation.run": "c" * 32}),
            "wrong_purpose": lambda c: c["Config"]["Labels"].update({"collegeai.validation.purpose": "academic-setup"}),
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
            self.assertEqual(target.validate_cleanup_target(CONTAINER_ID, RUN_TOKEN, PURPOSE), CONTAINER_ID)
        self.assertIn(target.docker_arguments("inspect", CONTAINER_ID), calls)
        self.assertFalse(any("{{ index" in str(arg) for call in calls for arg in call))
        self.assertFalse(any("exec" in call or "stop" in call for call in calls))

    def test_rejects_stopped_container_for_database_operations(self):
        value = inspected_container()
        value["State"]["Running"] = False
        with self.assertRaisesRegex(RuntimeError, "not running"):
            self.call_with(value)

    def test_remote_or_unavailable_engine_and_inspect_fail_closed(self):
        for mode in ["remote_context", "remote_endpoint", "wrong_engine", "inspect_failed", "malformed_json"]:
            with self.subTest(mode=mode):
                with self.assertRaises((RuntimeError, ValueError)):
                    self.call_with(inspected_container(), mode=mode)

    def test_rejects_docker_environment_overrides(self):
        for name in ["DOCKER_HOST", "DOCKER_CONTEXT"]:
            with self.subTest(variable=name), patch.dict(os.environ, {name: "remote"}), patch("subprocess.run", side_effect=AssertionError("subprocess reached")):
                with self.assertRaises(RuntimeError):
                    target.validate_local_engine()


class HelperSafetyTests(unittest.TestCase):
    HELPERS = {
        "academic_setup_concurrency": "academic-setup",
        "faculty_assignment_concurrency": "faculty-assignment",
        "faculty_attendance_concurrency": "faculty-attendance",
        "faculty_tests_concurrency": "faculty-tests",
    }

    def setUp(self):
        env = patch.dict(os.environ, {"DOCKER_HOST": "", "DOCKER_CONTEXT": ""})
        env.start()
        self.addCleanup(env.stop)
        self.modules = {name: importlib.import_module(name) for name in self.HELPERS}
        for module in self.modules.values():
            if hasattr(module, "CONTAINER"):
                module.CONTAINER = None

    def test_imports_have_no_docker_or_database_side_effects(self):
        with patch("subprocess.run", side_effect=AssertionError("subprocess reached")), patch("subprocess.Popen", side_effect=AssertionError("Popen reached")):
            for module in self.modules.values():
                importlib.reload(module)

    def test_all_helpers_reject_persistent_name_and_full_id_before_sql(self):
        for name, purpose in self.HELPERS.items():
            for supplied_id in ["supabase_db_CollegeAIChatbot", CONTAINER_ID]:
                with self.subTest(helper=name, target=supplied_id):
                    container = inspected_container(purpose=purpose)
                    container["Name"] = "/supabase_db_CollegeAIChatbot"
                    container["Mounts"] = [{"Type": "volume", "Destination": target.DATA_DIRECTORY}]
                    with patch("subprocess.run", side_effect=mock_commands(container, [])), patch("subprocess.Popen", side_effect=AssertionError("Popen reached")):
                        with self.assertRaises(RuntimeError):
                            self.modules[name].main([supplied_id, RUN_TOKEN, purpose])

    def test_sql_requires_configuration_for_every_helper(self):
        with patch("subprocess.run", side_effect=AssertionError("subprocess reached")):
            for name, module in self.modules.items():
                with self.subTest(helper=name), self.assertRaisesRegex(RuntimeError, "configured"):
                    module.sql("never executed")

    def test_failed_reconfiguration_clears_imported_target(self):
        attendance = self.modules["faculty_attendance_concurrency"]
        tests = self.modules["faculty_tests_concurrency"]
        with patch("subprocess.run", side_effect=mock_commands(inspected_container(), [])):
            attendance.configure_target(CONTAINER_ID, RUN_TOKEN, PURPOSE)
        with self.assertRaises(RuntimeError):
            attendance.configure_target("supabase_db_CollegeAIChatbot", RUN_TOKEN, PURPOSE)
        self.assertIsNone(attendance.CONTAINER)
        with self.assertRaisesRegex(RuntimeError, "configured"):
            tests.sql("never executed")

    def test_failed_cli_parse_clears_previous_target(self):
        for name, module in self.modules.items():
            with self.subTest(helper=name):
                module.CONTAINER = CONTAINER_ID
                module_attendance = self.modules["faculty_attendance_concurrency"]
                module_attendance.CONTAINER = CONTAINER_ID
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    module.main([])
                if name == "faculty_tests_concurrency":
                    self.assertIsNone(module_attendance.CONTAINER)
                else:
                    self.assertIsNone(module.CONTAINER)

    def test_imported_assessment_sql_uses_exact_attendance_id_and_pinned_context(self):
        attendance = self.modules["faculty_attendance_concurrency"]
        tests = self.modules["faculty_tests_concurrency"]
        with patch("subprocess.run", side_effect=mock_commands(inspected_container(), [])):
            attendance.configure_target(CONTAINER_ID, RUN_TOKEN, PURPOSE)
        with patch("subprocess.run") as run:
            tests.sql("not executed")
            argv = run.call_args.args[0]
            self.assertEqual(argv[:6], ["docker", "--context", "desktop-linux", "exec", "-i", CONTAINER_ID])

    def test_fixture_paths_resolve_from_helper_location_outside_checkout(self):
        old_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as unrelated:
            try:
                os.chdir(unrelated)
                for name in ["faculty_attendance_concurrency", "faculty_tests_concurrency"]:
                    module = self.modules[name]
                    purpose = self.HELPERS[name]
                    paths = []
                    read_text = Path.read_text
                    def record_read(path, *args, **kwargs):
                        paths.append(path)
                        return read_text(path, *args, **kwargs)
                    with self.subTest(helper=name), patch("subprocess.run", side_effect=mock_commands(inspected_container(purpose=purpose), [])), patch.object(Path, "read_text", record_read), patch.object(module, "sql", side_effect=RuntimeError("fixture read completed")):
                        with self.assertRaisesRegex(RuntimeError, "fixture read completed"):
                            module.main([CONTAINER_ID, RUN_TOKEN, purpose])
                    expected = Path(module.__file__).resolve().with_name(name.replace("_concurrency", "_database") + ".sql")
                    self.assertEqual(paths, [expected])
            finally:
                os.chdir(old_directory)

    def test_reset_runner_rejects_persistent_target_without_probe_or_sql(self):
        reset = importlib.import_module("verify_supabase_data_reset")
        calls = []
        def reject_persistent(argv, **kwargs):
            if argv[3:4] == ["run"]:
                from subprocess import CompletedProcess
                return CompletedProcess(argv, 0, "supabase_db_CollegeAIChatbot", "")
            return mock_commands(inspected_container(), calls)(argv, **kwargs)
        with patch("subprocess.run", side_effect=reject_persistent), self.assertRaisesRegex(RuntimeError, "valid ID"):
            reset.main()
        self.assertFalse(any("exec" in call or "stop" in call for call in calls))

    def reset_scenario(self, scenario):
        reset = importlib.import_module("verify_supabase_data_reset")
        container = inspected_container(purpose="data-reset")
        calls = []
        def run(argv, **kwargs):
            from subprocess import CompletedProcess
            operation = argv[3] if argv[:3] == ["docker", "--context", "desktop-linux"] else None
            if operation == "run":
                calls.append(argv)
                token = next(arg.split("=", 1)[1] for arg in argv if arg.startswith("collegeai.validation.run="))
                container["Name"] = "/" + target.expected_name(token, "data-reset")
                container["Config"]["Labels"]["collegeai.validation.run"] = token
                if scenario == "foreign":
                    container["Name"] = "/supabase_db_CollegeAIChatbot"
                if scenario == "volume":
                    container["Mounts"] = [{"Type": "volume", "Destination": target.DATA_DIRECTORY}]
                return CompletedProcess(argv, 1 if scenario == "creation_failed" else 0, CONTAINER_ID, "creation failed")
            if operation == "exec":
                calls.append(argv)
                if scenario != "bootstrap_failed" or argv[5] != "cat":
                    raise AssertionError("Database operation reached: " + repr(argv))
                raise RuntimeError("mock bootstrap failure")
            if operation == "stop":
                calls.append(argv)
                return CompletedProcess(argv, 0, CONTAINER_ID, "")
            return mock_commands(container, calls)(argv, **kwargs)
        with contextlib.redirect_stdout(io.StringIO()), patch("subprocess.run", side_effect=run), self.assertRaises(RuntimeError):
            reset.main()
        return calls

    def test_reset_full_id_persistent_storage_rejected_and_owned_failure_cleaned(self):
        calls = self.reset_scenario("volume")
        self.assertFalse(any("exec" in call for call in calls))
        self.assertEqual([call for call in calls if "stop" in call], [target.docker_arguments("stop", "--timeout", "10", CONTAINER_ID)])

    def test_reset_foreign_full_id_never_probed_or_stopped(self):
        calls = self.reset_scenario("foreign")
        self.assertFalse(any("exec" in call or "stop" in call for call in calls))

    def test_reset_creation_failure_never_cleans_borrowed_id(self):
        calls = self.reset_scenario("creation_failed")
        self.assertFalse(any("exec" in call or "inspect" in call[3:4] or "stop" in call for call in calls))

    def test_reset_bootstrap_failure_cleans_only_validated_created_id(self):
        calls = self.reset_scenario("bootstrap_failed")
        probe = next(i for i, call in enumerate(calls) if "exec" in call)
        inspect = next(i for i, call in enumerate(calls) if call[3:4] == ["inspect"])
        self.assertLess(inspect, probe)
        self.assertEqual([call for call in calls if "stop" in call], [target.docker_arguments("stop", "--timeout", "10", CONTAINER_ID)])


if __name__ == "__main__":
    unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
