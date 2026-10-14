"""Stage 1.10 raw-file verification only; no preparation plan or runtime calls.

Run from repository root with python -B. Writes only the Stage 1.10 hash report
beside this file. Does not execute SQL, import a runner, inspect environments,
invoke processes, connect to services or authenticate approval.
"""
import ast
import hashlib
import json
import re
from pathlib import Path


REVIEW = Path("docs/reviews/student_enrollment_final_2026-10-11")
PACKAGE = Path("scripts/validation/b05_containment")
ALLOWED_CHANGED = {
    str(PACKAGE / name).replace("\\", "/")
    for name in ("README.md", "runner_contract.json", "test_matrix.md", "migration_manifest.json")
}


def identity(path):
    raw = Path(path).read_bytes()
    return {"path": str(path).replace("\\", "/"), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    baseline = json.loads((REVIEW / "B05_STAGE_1_10_ENTRY_HASHES.json").read_bytes())
    old = json.loads((REVIEW / "B05_STAGE_1_9_OFFLINE_HASH_EVIDENCE.json").read_bytes())
    manifest = json.loads((PACKAGE / "migration_manifest.json").read_bytes())
    contract = json.loads((PACKAGE / "runner_contract.json").read_bytes())
    entries = manifest["migrations"] + manifest["pinned_inputs"]
    require(len(manifest["migrations"]) == 40 and len(manifest["pinned_inputs"]) == 12, "Inventory size changed")
    require([e["path"] for e in entries] == [e["path"] for e in old["results"]], "Pinned input identity/order changed")
    comparisons = []
    for entry in entries:
        observed = identity(entry["path"])
        require((observed["sha256"], observed["bytes"]) == (entry["sha256"], entry["bytes"]), "Pin mismatch: " + entry["path"])
        comparisons.append({**observed, "hash_match": True, "length_match": True})
    migrations = manifest["migrations"]
    require([e["filename"] for e in migrations] == sorted(p.name for p in Path("supabase/migrations").glob("*.sql")), "Migration set/order mismatch")
    versions = [e["version"] for e in migrations]
    require(len(set(versions)) == 40 and versions == sorted(versions), "Migration versions mismatch")
    for number, entry in enumerate(migrations, 1):
        require(entry["order"] == number and re.fullmatch(r"\d{14}", entry["version"]), "Migration version/order invalid")
        require(entry["filename"] == entry["version"] + "_" + entry["migration_name"] + ".sql", "Migration name invalid")
        require(entry["path"] == "supabase/migrations/" + entry["filename"], "Migration path invalid")
        raw = Path(entry["path"]).read_text(encoding="utf-8")
        require(entry["file_transaction"] == bool(re.search(r"(?m)^\s*BEGIN;\s*$", raw)), "Declared transaction mismatch")
    changed, preserved = [], []
    for entry in baseline["files"]:
        observed = identity(entry["path"])
        if (observed["sha256"], observed["bytes"]) == (entry["sha256"], entry["bytes"]):
            preserved.append(observed)
        else:
            require(entry["path"] in ALLOWED_CHANGED, "Unexpected entry-file change: " + entry["path"])
            changed.append({"path": entry["path"], "before_sha256": entry["sha256"], "before_bytes": entry["bytes"], "after_sha256": observed["sha256"], "after_bytes": observed["bytes"]})
    require({e["path"] for e in changed} == ALLOWED_CHANGED, "Unexpected remediation change set")
    source = Path(manifest["successor_source"]).read_bytes()
    require(source == Path(manifest["successor_validation_copy"]).read_bytes(), "Successor copy drift")
    require(manifest["successor_ledger_version"] is None, "Successor ledger version prohibited")
    stops = []
    for path in (REVIEW / "SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql", Path(manifest["successor_source"]), Path(manifest["successor_validation_copy"])):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        markers = []
        for name in ("review_stop", "dependency_stop"):
            matches = [(n, line) for n, line in enumerate(lines, 1) if line.startswith("DO $" + name + "$ BEGIN RAISE EXCEPTION ")]
            require(len(matches) == 1, "Active unconditional stop missing: " + str(path))
            markers.append({"name": name, "line": matches[0][0], "statement": matches[0][1]})
        executable = [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("--")]
        require(executable[-1] == "ROLLBACK;", "Final rollback changed")
        stops.append({"path": str(path).replace("\\", "/"), "unconditional_stops": markers, "final_rollback_line": max(n for n, line in enumerate(lines, 1) if line.strip() == "ROLLBACK;")})
    ledger_statement = next(line for line in source.decode("utf-8").splitlines() if "IS DISTINCT FROM ARRAY['20250717000000'" in line)
    require(re.findall(r"'([0-9]{14})'", ledger_statement) == versions, "Successor ledger array mismatch")
    matrix = (PACKAGE / "test_matrix.md").read_text(encoding="utf-8")
    rows = [line for line in matrix.splitlines() if re.match(r"^\| M\d{2} \|", line)]
    require(len(rows) == 21 and [line.split("|")[1].strip() for line in rows] == [f"M{i:02}" for i in range(1, 22)], "Case inventory changed")
    require(all(line.endswith("| NOT RUN |") for line in rows), "Runtime status changed")
    require(re.findall(r"(?m)^### (M\d{2}) — NOT RUN$", matrix) == [f"M{i:02}" for i in range(1, 22)], "Detailed case status/coverage missing")
    for marker in ("**T1:", "**T2:", "**T3:", "**C:", "**A:", "GET STACKED DIAGNOSTICS", "Assertions and the evidence marker are outside the catch", "Exhaustive expected PostgreSQL-error inventory", "BEFORE CREATE/SQL", "Invitation expired during finalization", "before elapsed lock", "Review public TRUNCATE triggers before resetting data"):
        require(marker in matrix, "Specification marker missing: " + marker)
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    decisions = [line for line in readme.splitlines() if re.match(r"^\| B\d{2} \|", line)]
    require([line.split("|")[1].strip() for line in decisions] == [f"B{i:02}" for i in range(1, 8)], "Decision register missing")
    require(contract["contract_version"] == 3 and contract["stage"] == manifest["stage"] == "1.10", "Stage mismatch")
    require(contract["execution_authorized"] is False and contract["runtime_adapter"] is None and contract["generic_purpose_registration"] is False and contract["runner_mode"] == "file_only_preparation", "Execution safeguard changed")
    require(contract["bootstrap_requirements"]["reviewed_startup_shim"] is None and contract["process_and_shutdown"]["reviewed_supervisor"] is None, "Unapproved component supplied")
    for section, keys in (("image_requirements", ("approved_repository_digest", "approved_content_image_id")), ("docker_control", ("approved_cli_absolute_path", "approved_cli_sha256", "approved_engine_id"))):
        require(all(contract[section][key] is None for key in keys), "Unapproved runtime pin selected")
    runtime = contract["runtime_prerequisite_identities"]
    for key in ("docker_cli_version", "engine_version", "engine_api_version", "docker_desktop_version_and_build", "postgres_toolchain_requirement", "extension_requirement", "startup_shim_version_hash_and_dependencies", "supervisor_version_hash_and_dependencies", "adapter_version_hash_and_dependencies", "offline_provider_fake_version_hash_and_loss_model", "independent_cleanup_observer_version_hash_and_release_mechanism", "approved_manifest_identity", "approved_probe_fault_barrier_and_derivative_identities"):
        require(key in runtime, "Required identity slot absent: " + key)
    for key, value in runtime.items():
        if key not in {"status", "specification", "version_selection", "postgres_toolchain_requirement", "extension_requirement", "image_verification", "cli_verification", "engine_verification", "effective_verification"}:
            require(value is None, "Unavailable identity silently filled: " + key)
    require(runtime["postgres_toolchain_requirement"]["server_version_num"] == 170006 and runtime["extension_requirement"]["vector"] == "0.8.0" and runtime["extension_requirement"]["btree_gist"] == "1.7", "Inherited requirements changed")
    require(all(value == "OPEN_OWNER_DECISION_UNRESOLVED" for value in contract["decision_register"]["status"].values()) and len(contract["decision_register"]["status"]) == 7, "Decision falsely closed")
    require(contract["decision_register"]["owner_identity"] is None and contract["decision_register"]["approvals"] is None, "Owner/approval invented")
    for key in ("reviewed_wrapper_artifact", "reviewed_rollback_successor_derivative", "reviewed_commit_successor_derivative"):
        require(contract["expected_error_handling"][key] is None, "Executable derivative/wrapper supplied")
    require(contract["expected_error_handling"]["on_error_stop"] is True, "Expected-error exit safeguard changed")
    # Syntax-only compilation; never import or call the preparation plan.
    preparation = (PACKAGE / "prepare.py").read_text(encoding="utf-8")
    tree = ast.parse(preparation)
    allowed_modules = {"__future__", "argparse", "hashlib", "json", "os", "re", "stat", "pathlib", "ctypes"}
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
    require(imports <= allowed_modules, "Preparation gained executable/network dependency")
    compile(preparation, str(PACKAGE / "prepare.py"), "exec")
    b05 = Path(migrations[-1]["path"]).read_text(encoding="utf-8")
    for fragment in ("Invitation expired during finalization' USING ERRCODE = '23514'", "Invitation acceptance requires reconciliation' USING ERRCODE = '55P03'", "Recorded identity mismatch' USING ERRCODE = '23514'", "Invalid operation transition' USING ERRCODE = '23514'", "CREATE TRIGGER trg_b05_lifecycle_no_truncate", "RETURN jsonb_build_object('invalid_state', true)"):
        require(fragment in b05, "Claimed source anchor absent: " + fragment)
    reset = Path("scripts/maintenance/reset_supabase_data.sql").read_text(encoding="utf-8")
    require("(t.tgtype::integer & 32) <> 0 AND NOT t.tgisinternal" in reset and "Review public TRUNCATE triggers before resetting data" in reset, "Maintenance source anchor missing")
    require("users_auth_user_id_fkey" in Path(migrations[0]["path"]).read_text(encoding="utf-8"), "Auth FK source anchor missing")
    artifacts = [identity(REVIEW / name) for name in ("B05_STAGE_1_10_ENTRY_HASHES.json", "verify_b05_stage_1_10_offline.py", "B05_STAGE_1_10_BLOCKER_REMEDIATION_REPORT.md")]
    result = {
        "review_date": "2026-10-12 Asia/Calcutta",
        "verdict": "BLOCKERS REMAIN",
        "runtime_status": "NOT RUN",
        "execution_authorized": False,
        "verification_command": "python -B docs/reviews/student_enrollment_final_2026-10-11/verify_b05_stage_1_10_offline.py",
        "verification_limits": "Raw-byte/source/AST checks only; textual coverage markers do not establish oracle correctness, PostgreSQL behavior or component availability. No runner/preparation_plan/runtime invocation.",
        "manifest_identity": identity(PACKAGE / "migration_manifest.json"),
        "manifest_approval": "UNAPPROVED_CONSISTENCY_ONLY_RE_REVIEW_REQUIRED",
        "migration_count": 40,
        "pinned_input_count": 12,
        "raw_pin_matches": 52,
        "exact_sorted_file_set": True,
        "migration_identities_and_declared_boundaries_match": True,
        "entry_preserved_count": len(preserved),
        "entry_changed_count": len(changed),
        "successor_byte_identical": True,
        "source_stops_and_rollbacks": stops,
        "runtime_cases": {f"M{i:02}": "NOT RUN" for i in range(1, 22)},
        "decisions": contract["decision_register"]["status"],
        "results": comparisons,
        "changes_from_stage_1_9_entry": changed,
        "preserved_entry_files": preserved,
        "new_review_artifact_hashes": artifacts,
        "evidence_self_hash": "Excluded to avoid self-reference; externally hash this JSON when approving it."
    }
    (REVIEW / "B05_STAGE_1_10_OFFLINE_HASH_EVIDENCE.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS: 52/52 raw-byte hashes and lengths; 40/40 migration identities/order/declared transaction boundaries")
    print(f"PASS: {len(preserved)}/{len(baseline['files'])} entry files preserved; {len(changed)} allowed documentation/contract/manifest changes")
    print("PASS: original stops and final rollbacks; successor copy byte-identical; ledger array exact")
    print("PASS: 21 detailed case specifications NOT RUN; 7 decisions OPEN; unresolved pins retained; no execution adapter")
    print("PASS: preparation AST/syntax and source anchors; runtime behavior NOT VERIFIED")
    print("WROTE: " + str(REVIEW / "B05_STAGE_1_10_OFFLINE_HASH_EVIDENCE.json").replace("\\", "/"))


if __name__ == "__main__":
    main()
