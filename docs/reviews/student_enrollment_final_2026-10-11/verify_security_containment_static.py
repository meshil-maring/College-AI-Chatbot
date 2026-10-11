"""Source text checks only; no SQL execution, network, drivers or application imports.

Run at repository root: python -B docs/reviews/student_enrollment_final_2026-10-11/verify_security_containment_static.py
Uses the preservation baseline embedded in SECURITY_CONTAINMENT_STATIC_RESULTS.json.
The scanner is a bounded lexical inventory, not a PostgreSQL parser or ACL evaluator.
"""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULT = HERE / 'SECURITY_CONTAINMENT_STATIC_RESULTS.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def statements(text):
    # Keep line offsets while ignoring comments; dollar bodies and strings are opaque.
    buf, i, start = [], 0, 0
    while i < len(text):
        if text.startswith('--', i):
            end = text.find('\n', i)
            end = len(text) if end < 0 else end
            buf.append(' ' * (end - i))
            i = end
        elif text.startswith('/*', i):
            begin, depth, i = i, 1, i + 2
            while depth and i < len(text):
                if text.startswith('/*', i):
                    depth, i = depth + 1, i + 2
                elif text.startswith('*/', i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            assert depth == 0
            buf.append(''.join('\n' if c == '\n' else ' ' for c in text[begin:i]))
        elif text[i] in "'\"":
            begin, quote = i, text[i]
            i += 1
            while i < len(text):
                if text[i] == quote:
                    if text[i:i + 2] == quote * 2:
                        i += 2
                    else:
                        i += 1
                        break
                else:
                    i += 1
            else:
                raise AssertionError('Unclosed quote')
            buf.append(text[begin:i])
        elif text[i] == '$' and (m := re.match(r'\$(?:[A-Za-z_]\w*)?\$', text[i:])):
            tag = m.group()
            end = text.find(tag, i + len(tag))
            assert end >= 0
            buf.append(text[i:end + len(tag)])
            i = end + len(tag)
        elif text[i] == ';':
            raw = ''.join(buf)
            if raw.strip():
                offset = len(raw) - len(raw.lstrip())
                yield text.count('\n', 0, start + offset) + 1, raw.strip() + ';'
            buf, i = [], i + 1
            start = i
        else:
            buf.append(text[i])
            i += 1
    assert not ''.join(buf).strip(), 'Unterminated statement'


def canonical(value):
    value = re.sub(r'\s+', ' ', value.replace('"', '').strip()).lower()
    value = value.replace('timestamp with time zone', 'timestamptz').replace('time without time zone', 'time').replace('timestamp without time zone', 'timestamp')
    return re.sub(r'\bvector\(\d+\)', 'vector', value)


def signature(name, params, declaration=False):
    types = []
    # Current declarations have simple named inputs; defaults contain no commas.
    for param in params.split(',') if params.strip() else []:
        p = canonical(re.split(r'\bDEFAULT\b|=', param, flags=re.I)[0])
        if declaration:
            p = re.sub(r'^(?:in|inout|variadic)\s+', '', p)
            p = p.split(' ', 1)[1]
        types.append(p)
    return canonical(name) + '(' + ','.join(types) + ')'


def main():
    previous = json.loads(RESULT.read_text(encoding='utf-8'))
    baseline = previous['preservation_baseline']
    migrations = sorted((ROOT / 'supabase/migrations').glob('*.sql'))
    events, definitions, acl_events, renames, drops = [], [], [], [], []
    current = {}
    declaration = re.compile(r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+([\w".]+)\s*\((.*?)\)\s*RETURNS\b', re.I | re.S)
    reference = re.compile(r'([\w".]+)\s*\(((?:[^()]|\([^()]*\))*)\)')
    for path in migrations:
        source = path.relative_to(ROOT).as_posix()
        for line, raw in statements(path.read_text(encoding='utf-8')):
            normalized = re.sub(r'\s+', ' ', raw.replace('"', '')).strip()
            loc = {'source': source, 'line': line}
            if re.search(r'\b(GRANT|REVOKE|POLICY|TRIGGER|DEFAULT PRIVILEGES|ROW LEVEL SECURITY)\b', normalized, re.I):
                events.append({**loc, 'statement': raw})
            if m := declaration.match(raw):
                name = m[1] if '.' in m[1] else 'public.' + m[1]
                sig = signature(name, m[2], True)
                header = re.split(r'\bAS\s+\$', raw, maxsplit=1, flags=re.I)[0]
                item = {**loc, 'signature': sig, 'parameters': m[2].strip(),
                        'security_definer': bool(re.search(r'\bSECURITY\s+DEFINER\b', header, re.I)),
                        'returns_trigger': bool(re.search(r'RETURNS\s+trigger\b', header.replace('"', ''), re.I)),
                        'header': header.strip(),
                        'contains_auth_role_reference': bool(re.search(r'\bauth\s*\.\s*role\s*\(', normalized, re.I)),
                        'body_review': 'manual required; reference is not proof of effective authorization'}
                definitions.append(item)
                if sig not in current:
                    item['created_at'] = loc
                    item['prior_drop_count'] = sum(d['signature'] == sig for d in drops)
                else:
                    item['created_at'] = current[sig]['created_at']
                    item['prior_drop_count'] = current[sig]['prior_drop_count']
                current[sig] = item
            if m := re.match(r'(GRANT|REVOKE)\s+(.*?)\s+ON\s+FUNCTION\s+(.*?)\s+(TO|FROM)\s+([^;]+);', normalized, re.I | re.S):
                for ref in reference.finditer(m[3]):
                    acl_events.append({**loc, 'operation': m[1].upper(), 'privileges': m[2].upper(),
                                       'signature': signature(ref[1], ref[2]),
                                       'roles': [r.strip().lower() for r in m[5].split(',')]})
            if m := re.match(r'ALTER FUNCTION\s+([\w.]+)\((.*?)\)\s+RENAME TO\s+(\w+)', normalized, re.I):
                old, new = signature(m[1], m[2]), signature('public.' + m[3], m[2])
                renames.append({**loc, 'old': old, 'new': new})
                if old in current:
                    current[new] = {**current.pop(old), 'signature': new, 'renamed_at': loc}
                for event in acl_events:
                    if event['signature'] == old:
                        event = dict(event, signature=new, renamed_from=old)
                        # Original ACL event retained; carry it to renamed identity separately.
                        renames[-1].setdefault('inherited_acl_events', []).append(event)
            if re.match(r'DROP FUNCTION\b', normalized, re.I):
                for ref in reference.finditer(normalized):
                    sig = signature(ref[1], ref[2])
                    drops.append({**loc, 'signature': sig})
                    current.pop(sig, None)
    inventory = []
    for sig, definition in sorted(current.items()):
        related = [e for e in acl_events if e['signature'] == sig and (e['source'], e['line']) >= (definition['created_at']['source'], definition['created_at']['line'])]
        related += [e for r in renames if r['new'] == sig for e in r.get('inherited_acl_events', [])]
        roles = {r: 'creator/default/catalog dependent' for r in ['public', 'anon', 'authenticated', 'service_role']}
        for e in sorted(related, key=lambda x: (x['source'], x['line'])):
            for role in e['roles']:
                if role in roles:
                    roles[role] = 'explicit grant' if e['operation'] == 'GRANT' else 'explicit revoke'
        inventory.append({**definition, 'explicit_acl_state_only': roles, 'acl_events': related,
                          'unsafe_default_candidate': any(roles[r] != 'explicit revoke' for r in ['public', 'anon', 'authenticated'])})
    by_signature = {item['signature']: item for item in inventory}
    six = [
        'public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text)',
        'public.phase717_rotate_invitation_with_outbox(uuid,text,timestamptz,timestamptz,text,integer)',
        'public.phase717_claim_email_outbox(integer,integer,integer)',
        'public.phase717_complete_email_outbox(uuid,integer,text,text,text,text,timestamptz)',
        'public.phase717_resolve_email_outbox_context(uuid,text)',
        'public.phase718_reconcile_mailgun_event(text,text,text,text,text,timestamptz)',
    ]
    seven = 'public.phase717_create_invitation_with_outbox(uuid,text,text,timestamptz,uuid,text,text)'
    changes = [p for p, h in baseline.items() if not (ROOT / p).is_file() or sha(ROOT / p) != h]
    sql = HERE / 'student_enrollment_schema_review_draft.sql'
    draft = sql.read_text(encoding='utf-8')
    checks = {
        'all_39_source_migrations_inventoried': len(migrations) == 39,
        'preservation_baseline_unchanged': not changes,
        'unconditional_review_exception_retained': "RAISE EXCEPTION 'REVIEW ONLY: execution requires explicit approval and a new reviewed migration'" in draft,
        'final_rollback_retained': draft.rstrip().endswith('ROLLBACK;'),
        'source_has_explicit_client_function_defaults': all(f'GRANT ALL ON FUNCTIONS TO "{r}"' in migrations[0].read_text(encoding='utf-8') for r in ['anon', 'authenticated']),
        'source_has_later_schema_wide_service_dml': any('ON ALL TABLES IN SCHEMA public TO service_role' in p.read_text(encoding='utf-8') for p in migrations),
        'source_audit_guard_is_row_update_delete_only': 'BEFORE UPDATE OR DELETE ON "public"."admin_audit_log"' in (ROOT / 'supabase/migrations/20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql').read_text(encoding='utf-8'),
        'six_sensitive_signatures_have_public_only_source_revokes': all(
            sig in by_signature and by_signature[sig]['security_definer']
            and by_signature[sig]['explicit_acl_state_only']['public'] == 'explicit revoke'
            and all(by_signature[sig]['explicit_acl_state_only'][role] == 'creator/default/catalog dependent' for role in ['anon', 'authenticated'])
            and by_signature[sig]['explicit_acl_state_only']['service_role'] == 'explicit grant' for sig in six),
        'six_sensitive_bodies_have_no_textual_auth_role_reference': all(
            sig in by_signature and not by_signature[sig]['contains_auth_role_reference'] for sig in six),
        'seven_argument_invitation_has_explicit_client_denial': seven in by_signature and all(
            by_signature[seven]['explicit_acl_state_only'][role] == 'explicit revoke' for role in ['public', 'anon', 'authenticated']),
        'private_search_has_explicit_client_denial': all(
            by_signature['public.search_similar_chunks(extensions.vector,integer,uuid,uuid,uuid,uuid,uuid,text)']['explicit_acl_state_only'][role] == 'explicit revoke' for role in ['public', 'anon', 'authenticated']),
        'no_top_level_admin_audit_rls_policy_or_truncate_guard_found': not any(
            'admin_audit_log' in event['statement'].lower() and re.search(r'^(?:CREATE\s+POLICY|ALTER\s+TABLE\b[^;]+\bENABLE\s+ROW\s+LEVEL\s+SECURITY|CREATE\s+TRIGGER\b[^;]+\bTRUNCATE)', event['statement'], re.I | re.S)
            for event in events),
    }
    documents = ['SECURITY_CONTAINMENT_REVIEW.md', 'SECURITY_CONTAINMENT_CHANGE_PLAN.md']
    links = []
    for name in documents:
        content = (HERE / name).read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)', content):
            if '://' not in target:
                relative, _, fragment = target.partition('#')
                path = HERE / relative
                ok = path.is_file()
                if fragment.startswith('L') and fragment[1:].isdigit() and ok:
                    ok = int(fragment[1:]) <= len(path.read_text(encoding='utf-8').splitlines())
                links.append({'document': name, 'target': target, 'exists_and_line_in_bounds': ok})
    checks['report_link_targets_and_line_bounds'] = all(x['exists_and_line_in_bounds'] for x in links)
    checks['new_artifacts_have_no_trailing_whitespace'] = all(all(l == l.rstrip() for l in (HERE / name).read_text(encoding='utf-8').splitlines()) for name in documents + [Path(__file__).name])
    rpc_calls, dynamic_rpc_calls, backend_hashes = [], [], {}
    for path in sorted((ROOT / 'backend/app').rglob('*.py')):
        source_text = path.read_text(encoding='utf-8')
        matches = list(re.finditer(r'\.rpc\(\s*([\'"])(\w+)\1', source_text))
        dynamic = list(re.finditer(r'\.rpc\(\s*([A-Za-z_]\w*)\s*,', source_text))
        if matches or dynamic:
            source = path.relative_to(ROOT).as_posix()
            backend_hashes[source] = sha(path)
            rpc_calls.extend({'source': source, 'line': source_text.count('\n', 0, m.start()) + 1, 'routine_name': m[2]} for m in matches)
            dynamic_rpc_calls.extend({'source': source, 'line': source_text.count('\n', 0, m.start()) + 1, 'variable': m[1]} for m in dynamic)
    result = {
        'review_date': '2026-10-11', 'timezone': 'Asia/Calcutta', 'scope': 'source only',
        'reproduce': 'python -B docs/reviews/student_enrollment_final_2026-10-11/verify_security_containment_static.py',
        'method': 'comment/quote/dollar aware top-level statement scanner; bounded declaration/ACL regexes; no SQL parser or effective privilege model',
        'limitations': ['Creator identity, implicit PUBLIC privileges, dynamic SQL, global/schema defaults, bootstrap grants, column ACLs, views, role inheritance and actual catalog are not evaluated.', 'unsafe_default_candidate is an investigation flag, not proof of RPC reachability or exploitable behavior.', 'Auth role textual reference is not a call-graph or authorization proof. Manual findings are in the review.'],
        'automated_checks': checks, 'automated_checks_passed': all(checks.values()),
        'preservation_baseline': baseline, 'preservation_file_count': len(baseline), 'changed_existing_files': changes,
        'migration_hashes': {p.relative_to(ROOT).as_posix(): sha(p) for p in migrations},
        'enrollment_sql_sha256': sha(sql), 'security_source_events': events,
        'function_definition_history': definitions, 'function_renames': renames, 'function_drops': drops,
        'inventory_counts': {'migrations': len(migrations), 'function_declarations': len(definitions), 'final_source_signatures': len(inventory),
                             'unsafe_default_candidates': sum(item['unsafe_default_candidate'] for item in inventory),
                             'sensitive_public_only_revoked_signatures': len(six)},
        'source_function_inventory': inventory, 'link_checks': links,
        'literal_backend_rpc_calls': rpc_calls, 'dynamic_backend_rpc_calls_requiring_manual_trace': dynamic_rpc_calls,
        'backend_rpc_source_hashes': backend_hashes,
        'manual_review': {'status': 'completed source review; not automated proof', 'finding_ids': ['SC-01','SC-02','SC-03','SC-04','SC-05','SC-06','SC-07','SC-08'], 'reports': documents,
                          'reviewed_dependencies': ['Six/seven invitation overloads', 'outbox claim/complete/context and Mailgun HTTP HMAC boundary', 'Phase 8.1 assertions and invitation actor=target acceptance', 'faculty dynamic RPC wrappers and current literal wrapper callers', 'audit SELECT/INSERT repository consumers', 'authority identity/JWT binding and master/academic guards', 'existing private/public knowledge RPC client revocations'],
                          'read_only_shell_checks_run': ['git status --short', 'git diff --check', 'rg source searches', 'ancestor/review-directory AGENTS.md existence check'],
                          'git_diff_check_result': 'No whitespace errors; warnings about inaccessible user Git ignore config and existing line-ending conversion. New artifact whitespace checked separately by this scanner.',
                          'unknowns': ['current catalog/effective ACLs and migration ledger', 'deployment creators/global defaults outside source', 'service-key request claims/RLS mode', 'external consumers and live inherited/view/RPC bridges', 'accepted concurrent revocation/retention contracts']},
        'artifact_hashes': {name: sha(HERE / name) for name in documents + [Path(__file__).name]},
        'not_run': ['SQL', 'migrations', 'PostgreSQL parser', 'database connections/catalog queries', 'Docker', 'pytest', 'Vitest', 'validation harness', 'network or remote services'],
        'runtime_validation': 'NOT RUN', 'next_approval': 'Approve preparation of a separate review-only containment migration candidate and its exact object/signature allowlist. No execution approval is implied.'
    }
    RESULT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'checks': checks, 'migrations': len(migrations), 'function_definitions': len(definitions), 'current_source_signatures': len(inventory), 'preserved': len(baseline), 'changes': changes}))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
