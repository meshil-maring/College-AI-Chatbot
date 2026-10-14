"""Stage 1.12 local hash/source verification; writes only its new evidence JSON.

Never imports preparation code or invokes SQL, processes, services or a runner.
Run from repository root with python -B. Historical evidence is read-only.
"""
import ast
import hashlib
import json
import re
from pathlib import Path


REVIEW = Path("docs/reviews/student_enrollment_final_2026-10-11")
PACKAGE = Path("scripts/validation/b05_containment")
VERDICT = "TARGETED ORACLE FIXES COMPLETE — INDEPENDENT RE-REVIEW REQUIRED"
CHANGED = {(PACKAGE / name).as_posix() for name in (
    "test_matrix.md", "test_preparation_safety.py", "migration_manifest.json")}


def identity(path):
    path = Path(path)
    raw = path.read_bytes()
    return {"path": path.as_posix(), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    baseline = json.loads((REVIEW / "B05_STAGE_1_12_ENTRY_HASHES.json").read_bytes())
    historical = json.loads((REVIEW / "B05_STAGE_1_10_OFFLINE_HASH_EVIDENCE.json").read_bytes())
    manifest = json.loads((PACKAGE / "migration_manifest.json").read_bytes())
    contract = json.loads((PACKAGE / "runner_contract.json").read_bytes())
    entries = manifest["migrations"] + manifest["pinned_inputs"]
    require(len(entries) == 52 and len(manifest["migrations"]) == 40, "Unexpected pin count")
    require([e["path"] for e in entries] == [e["path"] for e in historical["results"]], "Pin identity/order changed")
    pins = []
    for entry in entries:
        actual = identity(entry["path"])
        require((actual["sha256"], actual["bytes"]) == (entry["sha256"], entry["bytes"]), "Pin mismatch: " + entry["path"])
        pins.append({**actual, "hash_match": True, "length_match": True})
    migrations = manifest["migrations"]
    versions = [e["version"] for e in migrations]
    require(len(set(versions)) == 40 and versions == sorted(versions), "Version mismatch")
    require([e["filename"] for e in migrations] == sorted(p.name for p in Path("supabase/migrations").glob("*.sql")), "Migration set/order mismatch")
    for number, entry in enumerate(migrations, 1):
        require(entry["order"] == number and re.fullmatch(r"\d{14}", entry["version"]), "Order/version invalid")
        require(entry["filename"] == entry["version"] + "_" + entry["migration_name"] + ".sql", "Name invalid")
        require(entry["path"] == "supabase/migrations/" + entry["filename"], "Path invalid")
        sql = Path(entry["path"]).read_text(encoding="utf-8")
        require(entry["file_transaction"] == bool(re.search(r"(?m)^\s*BEGIN;\s*$", sql)), "Declared boundary changed")
    preserved, changed = [], []
    require(len(baseline["files"]) == 118 and len({e["path"] for e in baseline["files"]}) == 118, "Entry inventory mismatch")
    for entry in baseline["files"]:
        actual = identity(entry["path"])
        if actual == entry:
            preserved.append(actual)
        else:
            require(entry["path"] in CHANGED, "Unexpected source change: " + entry["path"])
            changed.append({"before": entry, "after": actual})
    require({e["after"]["path"] for e in changed} == CHANGED, "Wrong targeted change set")
    source = Path(manifest["successor_source"]).read_bytes()
    require(source == Path(manifest["successor_validation_copy"]).read_bytes(), "Copy drift")
    require(manifest["successor_ledger_version"] is None, "Successor ledger prohibited")
    stops = []
    for path in (REVIEW / "SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql", Path(manifest["successor_source"]), Path(manifest["successor_validation_copy"])):
        sql = path.read_text(encoding="utf-8")
        lines = sql.splitlines()
        found = {name: [n for n, line in enumerate(lines, 1) if line.startswith("DO $" + name + "$ BEGIN RAISE EXCEPTION ")] for name in ("review_stop", "dependency_stop")}
        require(all(len(v) == 1 for v in found.values()) and sql.rstrip().endswith("ROLLBACK;"), "Stop/rollback changed")
        stops.append({"path": path.as_posix(), "stop_lines": found, "final_rollback_line": max(n for n, line in enumerate(lines, 1) if line.strip() == "ROLLBACK;")})
    ledger = next(line for line in source.decode("utf-8").splitlines() if "IS DISTINCT FROM ARRAY['20250717000000'" in line)
    require(re.findall(r"'([0-9]{14})'", ledger) == versions, "Ledger array drift")
    matrix = (PACKAGE / "test_matrix.md").read_text(encoding="utf-8")
    ids = [f"M{i:02}" for i in range(1, 22)]
    rows = [line for line in matrix.splitlines() if re.match(r"^\| M\d{2} \|", line)]
    require([line.split("|")[1].strip() for line in rows] == ids and all(line.endswith("| NOT RUN |") for line in rows), "Runtime case/status changed")
    require(re.findall(r"(?m)^### (M\d{2}) — NOT RUN$", matrix) == ids, "Detailed status changed")
    outbox_rows = [line for line in matrix.splitlines() if re.match(r"^\| OB12/M\d{2} \|", line)]
    require([line.split("|")[1].strip().split("/")[1] for line in outbox_rows] == ids and all(line.endswith("| NOT RUN |") for line in outbox_rows), "Outbox coverage/status missing")
    require(contract["execution_authorized"] is False and contract["runtime_adapter"] is None and contract["runner_mode"] == "file_only_preparation", "Runtime safeguard changed")
    require(contract["stage"] == manifest["stage"] == "1.10" and manifest["targeted_oracle_revision"]["stage"] == "1.12", "Revision/contract stage mismatch")
    require(len(contract["decision_register"]["status"]) == 7 and all(v == "OPEN_OWNER_DECISION_UNRESOLVED" for v in contract["decision_register"]["status"].values()), "Owner decision changed")
    # Syntax inspection only. The unchanged contract/preparation code are also
    # protected by the raw-entry checks; do not import them to verify anything.
    for path in (PACKAGE / "prepare.py", PACKAGE / "test_preparation_safety.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    artifacts = [identity(REVIEW / name) for name in (
        "B05_STAGE_1_12_ENTRY_HASHES.json", "B05_STAGE_1_12_TARGETED_ORACLE_REMEDIATION_REPORT.md", "verify_b05_stage_1_12_offline.py")]
    for path in [Path(change["after"]["path"]) for change in changed] + [Path(e["path"]) for e in artifacts]:
        require(all(line.rstrip() == line for line in path.read_text(encoding="utf-8").splitlines()), "Trailing whitespace: " + str(path))
    evidence = {
        "review_date": "2026-10-12 Asia/Calcutta", "stage": "1.12", "verdict": VERDICT,
        "execution_authorized": False, "runtime_status": "NOT RUN",
        "verification_command": "python -B docs/reviews/student_enrollment_final_2026-10-11/verify_b05_stage_1_12_offline.py",
        "manifest_identity": identity(PACKAGE / "migration_manifest.json"),
        "manifest_approval": "UNAPPROVED_CONSISTENCY_ONLY_INDEPENDENT_RE_REVIEW_REQUIRED",
        "migration_count": 40, "pinned_input_count": 12, "raw_pin_matches": 52,
        "migration_identity_order_boundary_checks": True, "entry_file_count": 118,
        "entry_preserved_count": len(preserved), "entry_changed_count": len(changed),
        "results": pins, "preserved_entry_files": preserved, "changes_from_stage_1_12_entry": changed,
        "new_review_artifact_hashes": artifacts, "source_stops_and_rollbacks": stops,
        "successor_byte_identical": True, "runtime_cases": dict.fromkeys(ids, "NOT RUN"),
        "outbox_case_register": dict.fromkeys(ids, "NOT RUN"), "decisions": contract["decision_register"]["status"],
        "limits": "Local byte/AST/source-coverage consistency only; unit test results are reported separately. Does not prove SQLSTATE, time, transaction, runtime availability, provider/worker behavior, consumers or authentication; no owner approval.",
        "evidence_self_hash": "Excluded to avoid self-reference; externally hash this evidence for independent review."
    }
    output = REVIEW / "B05_STAGE_1_12_OFFLINE_HASH_EVIDENCE.json"
    output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("PASS: 52/52 raw-byte pins; 40/40 migration identities/order/declared boundaries")
    print(f"PASS: {len(preserved)}/118 entry files preserved; exactly {len(changed)} allowed preparation/test/manifest changes")
    print("PASS: source/copy stops and final rollbacks; successor equality; exact ledger array")
    print("PASS: M01-M21 and OB12 register NOT RUN; unchanged runtime contract; B01-B07 OPEN")
    print("PASS: changed/new source whitespace; AST syntax only; no runtime behavior verified")
    print("WROTE: " + output.as_posix())


if __name__ == "__main__":
    main()
