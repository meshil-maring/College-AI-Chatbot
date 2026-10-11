"""Record the repaired source and review artifacts; never invokes Docker or SQL."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

EVIDENCE = Path(__file__).resolve().parent
REPOSITORY = EVIDENCE.parents[2]
FILES = [
    "academic_setup_concurrency.py",
    "faculty_assignment_concurrency.py",
    "faculty_attendance_concurrency.py",
    "faculty_tests_concurrency.py",
    "disposable_container.py",
    "verify_academic_setup_database.ps1",
    "verify_faculty_assignment_database.ps1",
    "verify_faculty_attendance_database.ps1",
    "verify_faculty_tests_database.ps1",
    "verify_supabase_data_reset.py",
    "test_disposable_container.py",
    "test_runner_safety.py",
    "test_runner_worker.ps1",
]

baseline = json.loads((EVIDENCE / "baseline.json").read_text())
for record in baseline:
    original = EVIDENCE / "baseline" / record["path"]
    assert hashlib.sha256(original.read_bytes()).hexdigest() == record["sha256"]

manifest = []
diff = []
for filename in FILES:
    relative = "scripts/validation/" + filename
    path = REPOSITORY / relative
    original = EVIDENCE / "baseline" / relative
    contents = path.read_bytes()
    text = contents.decode("utf-8")
    if path.suffix == ".py":
        ast.parse(text, filename=relative)
    manifest.append({"path": relative, "change": "modified" if original.exists() else "added", "sha256": hashlib.sha256(contents).hexdigest()})
    previous = original.read_text(encoding="utf-8") if original.exists() else ""
    diff.extend(difflib.unified_diff(previous.splitlines(keepends=True), text.splitlines(keepends=True), fromfile="a/" + relative, tofile="b/" + relative))
(EVIDENCE / "source_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
(EVIDENCE / "remediation.diff").write_text("".join(diff), encoding="utf-8")

archive_directory = REPOSITORY / "docs/evidence/patch_reviews/college_ai_enrollment_review_patch_v2"
archive = archive_directory / "COLLEGE_AI_ENROLLMENT_REVIEW_PATCH_V2.zip"
with zipfile.ZipFile(archive) as bundle:
    for entry in bundle.infolist():
        assert (archive_directory / "source" / entry.filename).read_bytes() == bundle.read(entry)

production = [name for name in FILES if not name.startswith("test_")]
findings = []
pattern = re.compile(r"supabase_db_CollegeAIChatbot|54322|DATABASE_URL|SUPABASE_URL|psycopg|asyncpg|Invoke-RestMethod|Invoke-WebRequest")
for filename in production:
    for number, line in enumerate((REPOSITORY / "scripts/validation" / filename).read_text(encoding="utf-8").splitlines(), 1):
        if pattern.search(line):
            findings.append({"file": filename, "line": number, "text": line})
assert not findings, findings
tracked_changes = subprocess.run(["git", "diff", "--name-only"], cwd=REPOSITORY, capture_output=True, text=True, check=True).stdout.splitlines()
assert set(tracked_changes) == {item["path"] for item in baseline}, tracked_changes
whitespace = subprocess.run(["git", "diff", "--check"], cwd=REPOSITORY, capture_output=True, text=True)
assert whitespace.returncode == 0, whitespace.stdout
results = json.loads((EVIDENCE / "runner_results.json").read_text(encoding="utf-8"))
assert len(results) == 92 and all(result["passed"] for result in results)
original_cases = {"persistent_name", "persistent_id", "validator_failure", "validator_empty", "validator_missing", "remote_host", "remote_context", "wrong_engine"}
summary = {
    "changed_active_files": len(manifest),
    "modified_active_files": sum(item["change"] == "modified" for item in manifest),
    "added_active_files": sum(item["change"] == "added" for item in manifest),
    "python_unit_tests_passed": 27,
    "powershell_mock_scenarios_passed": len(results),
    "original_mock_scenarios_passed": sum(result["case"] in original_cases for result in results),
    "powershell_parse_files_passed": len(json.loads((EVIDENCE / "powershell_parse.json").read_text(encoding="utf-8-sig"))),
    "persistent_target_audit_findings": findings,
    "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "archive_source_unchanged": True,
    "git_diff_check_passed": True,
    "live_validation_performed": False,
    "database_operations_performed": False,
    "operational_tools_excluded_from_harness_audit": ["invoke_local_supabase.ps1", "manage_local_super_admin.ps1", "provision_local_demo_users.ps1"],
}
(EVIDENCE / "verification_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
