"""Independent Stage 1.13 file checks. No SQL, preparation entrypoint or services.

Writes only new Stage 1.13 evidence/diffs; intercepts the Stage 1.12 writer.
The prior matrix contents are unavailable and are not reconstructed by guessing.
"""
import contextlib
import difflib
import hashlib
import io
import json
from pathlib import Path
import runpy
from unittest.mock import patch


REVIEW = Path("docs/reviews/student_enrollment_final_2026-10-11")
PACKAGE = Path("scripts/validation/b05_containment")


def identity(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": path.as_posix(), "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw)}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    baseline = json.loads((REVIEW / "B05_STAGE_1_12_ENTRY_HASHES.json").read_bytes())
    before = {r["path"]: r for r in baseline["files"]}
    evidence_path = REVIEW / "B05_STAGE_1_12_OFFLINE_HASH_EVIDENCE.json"
    supplied_raw = evidence_path.read_bytes()
    supplied = json.loads(supplied_raw)
    records = (supplied["results"] + supplied["preserved_entry_files"]
               + supplied["new_review_artifact_hashes"] + [supplied["manifest_identity"]])
    for row in records:
        actual = identity(row["path"])
        check(all(actual[k] == row[k] for k in actual), "Evidence drift: " + row["path"])
    preserved, changes = [], []
    for row in baseline["files"]:
        actual = identity(row["path"])
        if actual == row:
            preserved.append(actual)
        else:
            changes.append({"before": row, "after": actual})
    expected = {(PACKAGE / n).as_posix() for n in
                ("test_matrix.md", "test_preparation_safety.py", "migration_manifest.json")}
    check({r["after"]["path"] for r in changes} == expected, "Unexpected change set")
    check(len(preserved) == 115, "Preservation count")

    # Exact recovery is accepted only after matching the recorded raw identity.
    test_path = PACKAGE / "test_preparation_safety.py"
    test_raw = test_path.read_bytes()
    test_before = (test_raw.split(b"class TargetedOracleSourceTests", 1)[0]
                   + b'if __name__ == "__main__":\n    unittest.main()\n')
    manifest_path = PACKAGE / "migration_manifest.json"
    manifest_before = json.loads(manifest_path.read_bytes())
    manifest_before.pop("targeted_oracle_revision")
    for row in manifest_before["pinned_inputs"]:
        row.update({k: before[row["path"]][k] for k in ("sha256", "bytes")})
    manifest_before = (json.dumps(manifest_before, indent=4) + "\n").replace("\n", "\r\n").encode()
    diffs = []
    for path, old in ((test_path, test_before), (manifest_path, manifest_before)):
        row = before[path.as_posix()]
        check((len(old), hashlib.sha256(old).hexdigest()) == (row["bytes"], row["sha256"]),
              "Recovered baseline does not match: " + str(path))
        diffs.extend(difflib.unified_diff(old.decode().splitlines(keepends=True),
                     path.read_bytes().decode().splitlines(keepends=True),
                     fromfile="stage1.10/" + path.as_posix(),
                     tofile="stage1.12/" + path.as_posix()))
    # Normalize patch line endings only; file identities above remain raw.
    diff_text = "".join(diffs).replace("\r\n", "\n")
    diff_path = REVIEW / "B05_STAGE_1_13_VERIFIED_TEST_MANIFEST_DIFF.patch"

    captured = []
    stdout = io.StringIO()
    def capture(path, data, encoding=None, errors=None, newline=None):
        check(path == evidence_path, "Unexpected Stage 1.12 write")
        captured.append(data.replace("\n", "\r\n").encode(encoding or "utf-8"))
        return len(data)
    with patch.object(Path, "write_text", capture), contextlib.redirect_stdout(stdout):
        runpy.run_path(str(REVIEW / "verify_b05_stage_1_12_offline.py"), run_name="__main__")
    check(captured == [supplied_raw], "Stage 1.12 reproduction mismatch")
    check(evidence_path.read_bytes() == supplied_raw, "Historical evidence was changed")
    for path in (PACKAGE / "test_matrix.md", test_path, manifest_path, evidence_path,
                 REVIEW / "verify_b05_stage_1_13_offline.py"):
        check(all(line == line.rstrip() for line in path.read_text(encoding="utf-8").splitlines()),
              "Trailing whitespace: " + str(path))

    diff_path.write_bytes(diff_text.encode("utf-8"))
    result = {
        "stage": "1.13", "review_date": "2026-10-12 Asia/Calcutta",
        "execution_authorized": False, "runtime_status": "NOT RUN",
        "supplied_stage_1_12_evidence": identity(evidence_path),
        "supplied_evidence_records_verified": len(records),
        "stage_1_12_verifier_evidence_reproduced_byte_for_byte": True,
        "stage_1_12_verifier_output": stdout.getvalue().splitlines(),
        "entry_preserved_count": len(preserved), "entry_changed_count": len(changes),
        "changes": changes, "preserved_entry_files": preserved,
        "verified_exact_diff": identity(diff_path),
        "test_baseline_recovered_exactly": True,
        "manifest_baseline_recovered_exactly": True,
        "matrix_stage_1_10_baseline_available": False,
        "matrix_exact_stage_1_12_diff_verified": False,
        "source_oracle_findings": {
            "terminal_outbox": "SOURCE_CONSISTENT",
            "M12_cancellation": "SOURCE_CONSISTENT",
            "M19_tenant_isolation": "SOURCE_CONSISTENT"},
        "limits": "Hash/source checks only. Prior matrix hash does not reveal its contents or certify its actual diff. No SQL, runtime, provider, deployed-state or owner-approval evidence."
    }
    output = REVIEW / "B05_STAGE_1_13_INDEPENDENT_HASH_EVIDENCE.json"
    output.write_bytes((json.dumps(result, indent=2) + "\n").encode("utf-8"))
    print("PASS: supplied evidence records/current raw hashes; 115 preserved/3 changed")
    print("PASS: Stage 1.12 checks; byte-identical in-memory evidence; original untouched")
    print("PASS: exact hash-verified prior tests/manifest and unified diffs")
    print("PASS: changed-file whitespace; no SQL/runtime behavior verified")
    print("UNVERIFIED: exact prior matrix contents and Stage 1.12 matrix diff")
    print("WROTE: " + output.as_posix())
    print("WROTE: " + diff_path.as_posix())


if __name__ == "__main__":
    main()
