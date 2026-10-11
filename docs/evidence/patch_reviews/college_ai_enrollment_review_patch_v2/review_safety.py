"""Review the archived patch with mocked Docker only; never open a database."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "source/scripts/validation"
sys.path.insert(0, str(SCRIPTS))
import disposable_container as guard
from test_disposable_container import inspected_container, CONTAINER_ID, RUN_TOKEN

PURPOSES = {
    "academic_setup": "academic-setup",
    "faculty_assignment": "faculty-assignment",
    "faculty_attendance": "faculty-attendance",
    "faculty_tests": "faculty-tests",
}


def fake_docker(container, calls):
    def run(argv, **kwargs):
        calls.append(argv)
        if argv == ["docker", "context", "show"]:
            value = "desktop-linux\n"
        elif argv[:2] == ["docker", "info"]:
            value = "docker-desktop\n"
        elif argv[:2] == ["docker", "inspect"]:
            value = json.dumps([container])
        else:
            raise AssertionError(f"Database/mutation command reached: {argv}")
        return subprocess.CompletedProcess(argv, 0, value, "")
    return run


class HelperSafetyTests(unittest.TestCase):
    def test_all_helpers_reject_persistent_name_and_full_id(self):
        for stem, purpose in PURPOSES.items():
            for target in ["supabase_db_CollegeAIChatbot", CONTAINER_ID]:
                with self.subTest(helper=stem, target=target):
                    container = inspected_container()
                    container["Name"] = "/supabase_db_CollegeAIChatbot"
                    container["Config"]["Labels"]["collegeai.validation.purpose"] = purpose
                    # Even matching ownership labels must not admit a disk volume.
                    container["Mounts"] = [{"Type": "volume", "Destination": "/var/lib/postgresql/data"}]
                    calls = []
                    argv = [str(SCRIPTS / (stem + "_concurrency.py")), target, RUN_TOKEN, purpose]
                    with patch.dict(os.environ, {"DOCKER_HOST": ""}), patch.object(sys, "argv", argv), patch.object(subprocess, "run", side_effect=fake_docker(container, calls)), patch.object(subprocess, "Popen", side_effect=AssertionError("Popen reached")):
                        with self.assertRaisesRegex(RuntimeError, "64-character|persistent mounts"):
                            runpy.run_path(argv[0], run_name="__main__")
                    self.assertFalse(any(a[1] in {"exec", "cp", "stop", "run"} for a in calls))

    def test_guard_negative_matrix(self):
        cases = {
            "wrong_id": lambda c: c.update(Id="c" * 64),
            "not_running": lambda c: c.update(State={"Running": False}),
            "wrong_image": lambda c: c["Config"].update(Image="postgres:latest"),
            "missing_labels": lambda c: c["Config"].update(Labels={}),
            "wrong_purpose": lambda c: c["Config"]["Labels"].update({"collegeai.validation.purpose": "academic-setup"}),
            "bind_mount": lambda c: c["HostConfig"].update(Binds=["/disk:/data"]),
            "extra_mount": lambda c: c["Mounts"].append({"Type": "volume", "Destination": "/other"}),
            "not_auto_removed": lambda c: c["HostConfig"].update(AutoRemove=False),
            "missing_tmpfs": lambda c: c["HostConfig"].update(Tmpfs={}),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                container = inspected_container()
                mutate(container)
                calls = []
                with patch.dict(os.environ, {"DOCKER_HOST": ""}), patch.object(subprocess, "run", side_effect=fake_docker(container, calls)):
                    with self.assertRaises(RuntimeError):
                        guard.validate_disposable_target(CONTAINER_ID, RUN_TOKEN, "faculty-attendance")

    def test_unbounded_tmpfs_is_accepted(self):
        container = inspected_container()
        container["HostConfig"]["Tmpfs"]["/var/lib/postgresql/data"] = "rw"
        with patch.dict(os.environ, {"DOCKER_HOST": ""}), patch.object(subprocess, "run", side_effect=fake_docker(container, [])):
            self.assertEqual(guard.validate_disposable_target(CONTAINER_ID, RUN_TOKEN, "faculty-attendance"), CONTAINER_ID)

    def test_legacy_tmpfs_metadata_is_rejected(self):
        # --tmpfs populates HostConfig.Tmpfs separately from MountPoints in Moby.
        container = inspected_container()
        container["Mounts"] = []
        with patch.dict(os.environ, {"DOCKER_HOST": ""}), patch.object(subprocess, "run", side_effect=fake_docker(container, [])):
            with self.assertRaisesRegex(RuntimeError, "tmpfs"):
                guard.validate_disposable_target(CONTAINER_ID, RUN_TOKEN, "faculty-attendance")

    def test_compile_all_python_files(self):
        for path in SCRIPTS.glob("*.py"):
            with self.subTest(file=path.name):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")


def guard_proxy():
    """Run the runner's actual Python validation expression against a fake volume."""
    argv = sys.argv[2:]
    assert argv[0] == "-c", argv
    code = argv[1]
    target, token, purpose = argv[2:]
    container = inspected_container()
    container["Config"]["Labels"]["collegeai.validation.run"] = token
    container["Config"]["Labels"]["collegeai.validation.purpose"] = purpose
    container["Mounts"] = [{"Type": "volume", "Destination": "/var/lib/postgresql/data"}]
    sys.argv = ["-c", target, token, purpose]
    with patch.dict(os.environ, {"DOCKER_HOST": ""}), patch.object(subprocess, "run", side_effect=fake_docker(container, [])):
        exec(code, {"__name__": "__main__"})


def powershell_matrix():
    worker = ROOT / "runner_mock.ps1"
    executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    results = []
    with tempfile.TemporaryDirectory(prefix="collegeai-patch-review-") as temp:
        for stem in PURPOSES:
            for mode in ["persistent_name", "persistent_id", "validator_failure", "validator_empty", "validator_missing", "remote_host", "remote_context", "wrong_engine"]:
                log = Path(temp) / (stem + "-" + mode + ".jsonl")
                env = dict(os.environ, REVIEW_RUNNER=str(SCRIPTS / ("verify_" + stem + "_database.ps1")), REVIEW_LOG=str(log), REVIEW_MODE=mode, REVIEW_PYTHON=sys.executable, REVIEW_PROXY=str(Path(__file__).resolve()))
                env.pop("DOCKER_HOST", None)
                result = subprocess.run([str(executable), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(worker)], capture_output=True, text=True, env=env, timeout=20)
                calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
                dangerous = [a for a in calls if a[0] == "docker" and (a[1] in {"cp", "stop"} or (a[1] == "exec" and "psql" in a))]
                entry = {"runner": stem, "case": mode, "exit": result.returncode, "rejected_before_sql_copy_stop": result.returncode != 0 and not dangerous, "dangerous_calls": dangerous, "stdout": result.stdout, "stderr": result.stderr, "calls": calls}
                results.append(entry)
                print(f"{'PASS' if entry['rejected_before_sql_copy_stop'] else 'FAIL'}: {stem} / {mode}")
    (ROOT / "runner_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--guard-proxy":
        guard_proxy()
    else:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(HelperSafetyTests))
        matrix = powershell_matrix()
        print(f"PowerShell cases rejecting before SQL/copy/stop: {sum(r['rejected_before_sql_copy_stop'] for r in matrix)}/{len(matrix)}")
        sys.exit(0 if result.wasSuccessful() and all(r["rejected_before_sql_copy_stop"] for r in matrix) else 1)
