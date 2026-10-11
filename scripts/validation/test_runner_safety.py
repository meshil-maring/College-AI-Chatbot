"""Execute PowerShell runners against command doubles. No real Docker/SQL calls."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import disposable_container as guard
from test_disposable_container import CONTAINER_ID, inspected_container, mock_commands

SCRIPTS = Path(__file__).resolve().parent
RUNNERS = ["academic_setup", "faculty_assignment", "faculty_attendance", "faculty_tests"]
ORIGINAL_CASES = ["persistent_name", "persistent_id", "validator_failure", "validator_empty", "validator_missing", "remote_host", "remote_context", "wrong_engine"]
EXTRA_CASES = ["valid", "owned_storage_failure", "migration_copy_failure", "cleanup_wrong_token", "cleanup_wrong_name", "cleanup_malformed_json", "cleanup_inspect_failed", "cleanup_empty", "cleanup_mismatch", "stop_failed", "creation_failed", "validator_mismatch", "remote_endpoint", "remote_env_context", "tmpfs_unbounded"]


def guard_proxy():
    argv = sys.argv[2:]
    assert Path(argv[0]).name == "disposable_container.py"
    action = argv[1]
    mode = os.environ["REVIEW_MODE"]
    metadata_path = Path(os.environ["REVIEW_METADATA"])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig")) if metadata_path.exists() else {"token": "b" * 32, "purpose": "faculty-attendance"}
    container = inspected_container(metadata["purpose"], metadata["token"])
    if mode == "persistent_id":
        container["Name"] = "/supabase_db_CollegeAIChatbot"
        container["Mounts"] = [{"Type": "volume", "Destination": guard.DATA_DIRECTORY}]
    if mode in {"validator_failure", "validator_empty", "validator_missing", "validator_mismatch"} and action == "cleanup":
        container["Config"]["Labels"]["collegeai.validation.run"] = "c" * 32
    if mode == "owned_storage_failure":
        container["Mounts"] = [{"Type": "volume", "Destination": guard.DATA_DIRECTORY}]
    if mode == "tmpfs_unbounded":
        container["HostConfig"]["Tmpfs"][guard.DATA_DIRECTORY] = "rw"
    if mode == "cleanup_wrong_token" and action == "cleanup":
        container["Config"]["Labels"]["collegeai.validation.run"] = "c" * 32
    if mode == "cleanup_wrong_name" and action == "cleanup":
        container["Name"] = "/supabase_db_CollegeAIChatbot"
    fake_mode = mode
    if action == "cleanup" and mode == "cleanup_malformed_json":
        fake_mode = "malformed_json"
    if action == "cleanup" and mode == "cleanup_inspect_failed":
        fake_mode = "inspect_failed"
    fake = mock_commands(container, [], fake_mode)
    def run(argv, **kwargs):
        with Path(os.environ["REVIEW_LOG"]).open("a", encoding="utf-8") as log:
            log.write(json.dumps(["guard-subprocess", *argv]) + "\n")
        return fake(argv, **kwargs)
    with patch("subprocess.run", side_effect=run), patch("subprocess.Popen", side_effect=AssertionError("Guard Popen reached")):
        guard.main(argv[1:])


def runner_case(stem, mode, temporary):
    executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    log = temporary / f"{stem}-{mode}.jsonl"
    metadata = temporary / f"{stem}-{mode}.metadata.json"
    env = dict(os.environ, REVIEW_RUNNER=str(SCRIPTS / f"verify_{stem}_database.ps1"), REVIEW_LOG=str(log), REVIEW_MODE=mode, REVIEW_PYTHON=sys.executable, REVIEW_PROXY=str(Path(__file__).resolve()), REVIEW_METADATA=str(metadata))
    env.pop("DOCKER_HOST", None)
    env.pop("DOCKER_CONTEXT", None)
    result = subprocess.run([str(executable), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPTS / "test_runner_worker.ps1")], capture_output=True, text=True, env=env, cwd=temporary, timeout=60)
    calls = [json.loads(line.lstrip("\ufeff")) for line in log.read_text(encoding="utf-8-sig").splitlines()] if log.exists() else []
    docker_calls = [call for call in calls if call[0] == "docker"]
    stops = [call for call in docker_calls if call[3] == "stop"]
    copies = [call for call in docker_calls if call[3] == "cp"]
    probes = [call for call in docker_calls if call[3] == "exec"]
    expected_success = mode == "valid"
    expected_stop = mode in {"valid", "owned_storage_failure", "tmpfs_unbounded", "migration_copy_failure", "stop_failed"}
    validation_failure = mode in set(ORIGINAL_CASES + ["owned_storage_failure", "tmpfs_unbounded", "creation_failed", "validator_mismatch", "remote_endpoint", "remote_env_context"])
    issues = []
    if (result.returncode == 0) != expected_success:
        issues.append(f"wrong exit status: {result.returncode}")
    if len(stops) != int(expected_stop):
        issues.append(f"wrong cleanup count: {len(stops)}")
    if validation_failure and (copies or probes):
        issues.append("copy/readiness/SQL reached before target validation")
    for call in docker_calls:
        if call[1:3] != ["--context", "desktop-linux"]:
            issues.append("Docker command is not pinned")
        if call[3] == "exec" and call[4] != CONTAINER_ID:
            issues.append("exec used another target")
        if call[3] == "cp" and not call[-1].startswith(CONTAINER_ID + ":"):
            issues.append("copy used another target")
        if call[3] == "stop" and call[4:] != ["--timeout", "10", CONTAINER_ID]:
            issues.append("cleanup used another target/command")
    for call in calls:
        if call[0] == "python" and Path(call[1]).name != "disposable_container.py":
            if call[2] != CONTAINER_ID or len(call) != 5:
                issues.append("imported concurrency helper did not receive full ID/token/purpose")
    if mode == "valid":
        run = next(call for call in docker_calls if call[3] == "run")
        if "--rm" not in run or "--network" not in run or run[run.index("--network") + 1] != "none":
            issues.append("creation isolation is missing")
        if run[run.index("--tmpfs") + 1] != guard.DATA_DIRECTORY + ":rw,size=536870912":
            issues.append("native tmpfs creation option changed")
        if "PGDATA=" + guard.DATA_DIRECTORY not in run:
            issues.append("creation data directory changed")
        if not copies or not probes:
            issues.append("valid scenario did not reach command doubles")
        # The actual guard runs plain JSON inspect on the exact ID before stop.
        inspected = [call for call in calls if call[:5] == ["guard-subprocess", "docker", "--context", "desktop-linux", "inspect"]]
        if len(inspected) != 2 or any(call[5:] != [CONTAINER_ID] for call in inspected):
            issues.append("target/cleanup inspection did not use plain JSON and exact ID")
    return {"runner": stem, "case": mode, "passed": not issues, "issues": issues, "exit": result.returncode, "calls": calls, "stdout": result.stdout, "stderr": result.stderr}


@unittest.skipUnless(os.name == "nt", "Windows PowerShell is required for mocked runner execution")
class PowerShellRunnerTests(unittest.TestCase):
    def test_original_32_and_runtime_regressions(self):
        with tempfile.TemporaryDirectory(prefix="collegeai-harness-mocks-") as directory:
            tasks = [(stem, mode, Path(directory)) for stem in RUNNERS for mode in ORIGINAL_CASES + EXTRA_CASES]
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda args: runner_case(*args), tasks))
        evidence = os.environ.get("COLLEGEAI_HARNESS_EVIDENCE")
        if evidence:
            path = Path(evidence)
            path.mkdir(parents=True, exist_ok=True)
            (path / "runner_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        for result in results:
            with self.subTest(runner=result["runner"], case=result["case"]):
                self.assertTrue(result["passed"], json.dumps({"issues": result["issues"], "exit": result["exit"], "stderr": result["stderr"][-2500:]}, indent=2))
        for stem in RUNNERS:
            values = [value for value in results if value["runner"] == stem]
            print(f"{stem}: {sum(value['passed'] for value in values)}/{len(values)} mocked scenarios passed", flush=True)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--guard-proxy"]:
        guard_proxy()
    else:
        unittest.main(testRunner=unittest.TextTestRunner(stream=sys.stdout, verbosity=2))
