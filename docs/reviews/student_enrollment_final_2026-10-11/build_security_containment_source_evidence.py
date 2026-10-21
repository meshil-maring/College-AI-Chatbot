"""Review-only file inventory. No SQL, application imports, network or subprocesses.

Run from the repository root with python -B on this file. Writes only the two
new source-evidence artifacts, never the candidate or any existing verifier result.
Lexical inventories are navigation aids, not PostgreSQL or authorization proof.
"""
from pathlib import Path
import ast
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    # Compile only three inspected, pure lexical helper definitions. Never import
    # the old verifier: its main() rewrites original results.
    parser_path = HERE / "verify_security_containment_static.py"
    tree = ast.parse(parser_path.read_text(encoding="utf-8"))
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name in {"statements", "canonical", "signature"}]
    assert len(selected) == 3
    lexical = {"re": re}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(parser_path), "exec"), lexical)
    statements, canonical, signature = (lexical[n] for n in ("statements", "canonical", "signature"))
    candidate = json.loads((HERE / "SECURITY_CONTAINMENT_CANDIDATE_RESULTS.json").read_text(encoding="utf-8"))
    prior = json.loads((HERE / "SECURITY_CONTAINMENT_STATIC_RESULTS.json").read_text(encoding="utf-8"))
    migrations = sorted((ROOT / "supabase/migrations").glob("*.sql"))
    declaration = re.compile(r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+([\w".]+)\s*\((.*?)\)\s*RETURNS\b', re.I | re.S)
    reference = re.compile(r'([\w".]+)\s*\(((?:[^()]|\([^()]*\))*)\)')
    current, history, acl_events, defaults, owners, triggers, renames, drops = {}, [], [], [], [], [], [], []
    manifest = {}
    for path in migrations:
        source = path.relative_to(ROOT).as_posix()
        manifest[source] = sha(path)
        for line, raw in statements(path.read_text(encoding="utf-8")):
            loc = {"source": source, "line": line}
            normalized = re.sub(r'\s+', ' ', raw.replace('"', '')).strip()
            if m := declaration.match(raw):
                name = m[1] if "." in m[1] else "public." + m[1]
                sig = signature(name, m[2], True)
                body_start = re.search(r'\bAS\s+(\$(?:[A-Za-z_]\w*)?\$)', raw, re.I)
                assert body_start, f"Unsupported body at {source}:{line}"
                header = raw[:body_start.start()].strip()
                body = raw[body_start.end():raw.rfind(body_start[1])]
                parameters = []
                for param in m[2].split(",") if m[2].strip() else []:
                    before = re.split(r'\bDEFAULT\b|=', param, maxsplit=1, flags=re.I)[0]
                    parts = canonical(before).split(" ", 1)
                    parameters.append({"name": parts[0], "type": parts[1],
                                       "has_default": bool(re.search(r'\bDEFAULT\b|=', param, re.I))})
                mode = "DEFINER" if re.search(r'\bSECURITY\s+DEFINER\b', header, re.I) else "INVOKER"
                search = re.search(r'\bSET\s+search_path\s*=\s*(.*?)(?=\s+SET\s+|$)', header, re.I | re.S)
                item = {**loc, "signature": sig, "parameters": parameters, "header": header,
                        "security_mode": mode, "declared_search_path": search[1].strip() if search else "not specified",
                        "body_sha256_utf8": hashlib.sha256(body.encode()).hexdigest(),
                        "statement_sha256_utf8": hashlib.sha256(raw.encode()).hexdigest(),
                        "auth_role_text_reference": bool(re.search(r'\bauth\s*\.\s*role\s*\(', body.replace('"', ''), re.I)),
                        "auth_uid_text_reference": bool(re.search(r'\bauth\s*\.\s*uid\s*\(', body.replace('"', ''), re.I)),
                        "has_dynamic_execute_token": bool(re.search(r'\bEXECUTE\b', body, re.I)),
                        "_body": body,
                        "_body_line": line + raw[:body_start.end()].count("\n")}
                history.append({k: v for k, v in item.items() if not k.startswith("_")})
                replacing = bool(re.match(r'CREATE\s+OR\s+REPLACE', raw, re.I))
                item["source_acl_history"] = current[sig]["source_acl_history"][:] if replacing and sig in current else []
                current[sig] = item
            if m := re.match(r'(GRANT|REVOKE)\s+(.*?)\s+ON\s+FUNCTION\s+(.*?)\s+(TO|FROM)\s+([^;]+);', normalized, re.I | re.S):
                for ref in reference.finditer(m[3]):
                    sig = signature(ref[1], ref[2])
                    roles = [x.strip().lower() for x in re.sub(r'\s+(?:RESTRICT|CASCADE)\s*$', '', m[5], flags=re.I).split(",")]
                    event = {**loc, "signature": sig, "operation": m[1].upper(), "privileges": m[2].upper(), "roles": roles, "statement": raw}
                    acl_events.append(event)
                    if sig in current:
                        current[sig]["source_acl_history"].append(event)
            if re.match(r'ALTER DEFAULT PRIVILEGES\b', normalized, re.I):
                defaults.append({**loc, "statement": raw, "creator_identity_verified": False})
            if re.match(r'ALTER\s+(?:TABLE(?: ONLY)?|FUNCTION|SCHEMA).*\bOWNER TO\b', normalized, re.I):
                owners.append({**loc, "statement": raw, "note": "Declared owner is not creation-session evidence"})
            if re.match(r'CREATE(?: OR REPLACE)? TRIGGER\b', normalized, re.I):
                triggers.append({**loc, "statement": raw})
            if m := re.match(r'ALTER FUNCTION\s+([\w.]+)\((.*?)\)\s+RENAME TO\s+(\w+)', normalized, re.I):
                old, new = signature(m[1], m[2]), signature("public." + m[3], m[2])
                renames.append({**loc, "old": old, "new": new})
                if old in current:
                    item = current.pop(old)
                    item["signature"], item["renamed_at"] = new, loc
                    current[new] = item
            if re.match(r'DROP FUNCTION\b', normalized, re.I):
                for ref in reference.finditer(normalized):
                    sig = signature(ref[1], ref[2])
                    drops.append({**loc, "signature": sig})
                    current.pop(sig, None)

    names = {s.split("(")[0].split(".")[-1] for s in current}
    inventory = []
    for sig, item in sorted(current.items()):
        body, body_line = item.pop("_body"), item.pop("_body_line")
        calls = []
        for match in re.finditer(r'(?<![\w.])([\w".]+)\s*\(', body):
            name = canonical(match[1])
            if name.split(".")[-1] in names:
                calls.append({"name": name, "line": body_line + body[:match.start()].count("\n"),
                              "qualification": "qualified" if "." in name else "unqualified",
                              "resolution": "lexical candidate only; overload/runtime binding not established"})
        item["nested_routine_name_candidates"] = calls
        item["last_explicit_source_acl_operation"] = {r: "not explicitly specified" for r in ("public", "anon", "authenticated", "service_role")}
        for event in item["source_acl_history"]:
            for role in event["roles"]:
                if role in item["last_explicit_source_acl_operation"]:
                    item["last_explicit_source_acl_operation"][role] = event["operation"]
        item["declared_actor_inputs"] = [p["name"] for p in item["parameters"]
                                         if any(label in p["name"] for label in ("actor", "created_by", "decided_by"))]
        item["actual_creator_role"] = "UNRESOLVED"
        item["current_catalog_or_effective_privileges"] = "NOT COLLECTED"
        inventory.append(item)

    backend_calls = []
    for path in sorted((ROOT / "backend/app").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        found = []
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call):
                continue
            is_rpc = isinstance(call.func, ast.Attribute) and call.func.attr == "rpc"
            is_wrapper = isinstance(call.func, ast.Name) and call.func.id in {"rpc", "_rpc", "_attendance_rpc"}
            if not (is_rpc or is_wrapper):
                continue
            literals = [arg.value for arg in call.args[:2] if isinstance(arg, ast.Constant) and isinstance(arg.value, str)]
            dictionaries = [arg for arg in call.args if isinstance(arg, ast.Dict)]
            keys = [k.value for arg in dictionaries for k in arg.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]
            expansions = [ast.unparse(v) for arg in dictionaries for k, v in zip(arg.keys, arg.values) if k is None]
            found.append({"source": path.relative_to(ROOT).as_posix(), "line": call.lineno,
                          "call_kind": "rpc" if is_rpc else "wrapper", "routine_name": literals[0] if literals else None,
                          "parameter_keys": keys, "dictionary_expansions": expansions,
                          "dynamic_resolution": "manual trace required" if not literals else "literal source name; runtime routing not proven"})
        if found:
            backend_calls.extend(sorted(found, key=lambda x: x["line"]))
            manifest[path.relative_to(ROOT).as_posix()] = sha(path)

    extras = ["SECURITY_CONTAINMENT_INDEPENDENT_REVIEW.md", "SECURITY_CONTAINMENT_CHANGE_PLAN.md",
              "SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql", "SECURITY_CONTAINMENT_MIGRATION_REVIEW.md",
              "SECURITY_CONTAINMENT_CANDIDATE_RESULTS.json", "SECURITY_CONTAINMENT_STATIC_RESULTS.json",
              "SECURITY_CONTAINMENT_REVIEW.md", "verify_security_containment_static.py",
              "build_security_containment_source_evidence.py"]
    for name in extras:
        path = HERE / name
        manifest[path.relative_to(ROOT).as_posix()] = sha(path)
    additional_paths = [ROOT / p for p in ("scripts/maintenance/reset_supabase_data.sql", "backend/app/db/supabase.py",
        "backend/app/core/security/__init__.py",
        "backend/app/core/security/tokens.py",
        "backend/app/core/security/identity.py",
        "backend/app/core/security/roles.py",
        "backend/app/core/security/tenancy.py",
        "backend/app/core/security/permissions.py",
        "backend/app/core/security/dependencies.py",
        "backend/app/config.py", "backend/app/api/email/mailgun_webhooks.py",
        "backend/app/services/email/mailgun_webhooks.py", "backend/app/services/invitations/platform_admin_invitations.py",
        "scripts/validation/disposable_container.py", "docs/evidence/enrollment_harness_remediation/REVIEW.md")]
    additional_paths += list((ROOT / "scripts/validation").glob("verify_*database.ps1"))
    additional_paths += list((ROOT / "scripts/validation").glob("*concurrency.py"))
    additional_paths += [ROOT / "scripts/validation/verify_supabase_data_reset.py"]
    for path in additional_paths:
        manifest[path.relative_to(ROOT).as_posix()] = sha(path)
    candidate_text = (HERE / "SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql").read_text(encoding="utf-8")
    candidate_statements = list(statements(candidate_text))
    ids = re.findall(r'^-- (C\d{3}) \|', candidate_text, re.M)
    checks = {
        "source_migration_count_and_hashes_match": len(migrations) == 39 and all(sha(ROOT / p) == h for p, h in candidate["migration_hashes"].items()),
        "prior_source_identity_set_agrees": set(current) == {x["signature"] for x in prior["source_function_inventory"]},
        "artifact_hashes_match": all(sha(HERE / n) == h for n, h in candidate["artifact_hashes"].items()),
        "candidate_51_ordered_ids": ids == [f"C{i:03}" for i in range(1, 52)] and len(candidate_statements) == 51,
        "unconditional_review_and_dependency_stops": candidate_statements[1][1].startswith("DO $review_stop$ BEGIN RAISE EXCEPTION") and candidate_statements[2][1].startswith("DO $dependency_stop$ BEGIN RAISE EXCEPTION"),
        "final_rollback_no_top_level_commit": candidate_statements[-1][1] == "ROLLBACK;" and not any(re.match(r'COMMIT\b', s, re.I) for _, s in candidate_statements),
    }
    assert all(checks.values()), checks
    result = {"review_date": "2026-10-11", "timezone": "Asia/Calcutta", "scope": "REVIEW ONLY; repository source",
        "method": "Inspected lexical helper definitions only, chronological SQL declaration/ACL/drop/rename inventory, Python AST call-site inventory; no main() from old verifier",
        "limitations": ["No PostgreSQL parser, body execution, privilege simulation, catalog, deployment or live creator evidence.",
            "Routine-name references are lexical candidates, not a resolved call graph; comments/dynamic strings may appear and overloads require review.",
            "Last explicit ACL operation excludes default/bootstrap/inherited/effective access and does not assert a full ACL state.",
            "Body and statement hashes cover decoded/scanned UTF-8 text; source_file_hashes cover original bytes.",
            "Backend RPC parameter dictionaries built in variables or expanded mappings require manual trace."],
        "counts": {"migration_files": len(migrations), "routine_declarations": len(history), "latest_source_identities": len(inventory),
            "latest_source_definers": sum(x["security_mode"] == "DEFINER" for x in inventory), "function_acl_events": len(acl_events),
            "default_acl_statements": len(defaults), "backend_rpc_and_wrapper_calls": len(backend_calls)},
        "source_file_hashes": manifest, "declaration_history": history, "latest_source_routines": inventory,
        "function_acl_events": acl_events, "default_acl_statements": defaults, "explicit_owner_statements": owners,
        "source_create_trigger_statements": triggers, "function_renames": renames, "function_drops": drops,
        "backend_rpc_and_wrapper_calls": backend_calls,
        "candidate_review_allowlists": {k: candidate[k] for k in ("approved_table_allowlist", "approved_sensitive_signatures", "approved_client_helper_signatures", "protected_service_signatures", "retained_trigger_bindings")},
        "source_only_checks": checks, "runtime_tests": {f"T{i:02}": "NOT RUN" for i in range(1, 15)}}
    (HERE / "SECURITY_CONTAINMENT_SOURCE_EVIDENCE.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    prose = ["# Security-containment routine and dependency inventory", "", "2026-10-11, Asia/Calcutta. **REVIEW ONLY; T01–T14 NOT RUN.**", "",
        "Generated from all 39 hashed migration files. This lists latest repository definitions after source replacements, drops and one rename; it does not describe the current catalog. The [JSON evidence](SECURITY_CONTAINMENT_SOURCE_EVIDENCE.json) retains declaration history, parameter names/default flags, source ACL events, defaults, owners, nested-name candidates and backend RPC/wrapper locations. The [blocker matrix](SECURITY_CONTAINMENT_BLOCKER_EVIDENCE_MATRIX.md) supplies acceptance criteria and manual analysis.", "",
        "G/R/? below mean last explicit source GRANT/REVOKE/no explicit event for that identity and role, respectively. They exclude creator defaults, global/bootstrap grants and inherited/effective access. Renamed definitions retain their source ACL history; replacements retain it. Nested names are lexical candidates and do not resolve overloads. `auth.role()` reference means text is present, not that every path checks it or that human identity is bound. Inspect bodies at the linked lines.", "",
        "| Exact latest source identity | Mode / declared search_path | auth.role text | Nested routine-name candidates | PUBLIC / anon / authenticated / service source events | Definition location |",
        "| --- | --- | --- | --- | --- | --- |"]
    for item in inventory:
        path, line = item["source"], item["line"]
        roles = "/".join({"GRANT": "G", "REVOKE": "R", "not explicitly specified": "?"}[item["last_explicit_source_acl_operation"][r]] for r in ("public", "anon", "authenticated", "service_role"))
        calls = ", ".join(sorted({x["name"] for x in item["nested_routine_name_candidates"]})) or "none found lexically"
        target = "../../../" + path + "#L" + str(line)
        mode_path = item["security_mode"] + " / " + item["declared_search_path"].replace("\n", " ")
        prose.append(f"| `{item['signature']}` | `{mode_path}` | {'yes' if item['auth_role_text_reference'] else 'no'} | {calls} | `{roles}` | [{Path(path).name}:{line}]({target}) |")
    prose += ["", "The proposed new guard `public.security_containment_prevent_audit_truncate()` is not part of the existing migration inventory. Candidate C046 declares it as SECURITY INVOKER with empty search_path; C047 revokes PUBLIC/client/service EXECUTE and C048 binds its rejecting statement trigger. Both candidate stops remain before these proposed statements. No future service-default removal contract or creator-state attestation is supplied by this inventory.", ""]
    (HERE / "SECURITY_CONTAINMENT_ROUTINE_INVENTORY.md").write_text("\n".join(prose), encoding="utf-8")
    print(json.dumps({"counts": result["counts"], "source_only_checks": checks, "runtime_tests": "T01–T14 NOT RUN"}, indent=2))


if __name__ == "__main__":
    main()
