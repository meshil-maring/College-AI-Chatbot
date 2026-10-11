"""Bounded text checks only. Never imports a DB driver or executes SQL.

Run from the repository root:
  .venv/Scripts/python.exe -B docs/reviews/student_enrollment_final_2026-10-11/verify_review_static.py
This lexer is not a PostgreSQL or PL/pgSQL parser.
"""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SQL = HERE / "student_enrollment_schema_review_draft.sql"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lex(text):
    """Discard comments; keep strings opaque; recursively check dollar bodies."""
    out, bodies, i = [], [], 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
        elif text.startswith("--", i):
            end = text.find("\n", i)
            i = len(text) if end == -1 else end + 1
        elif text.startswith("/*", i):
            depth, i = 1, i + 2
            while depth and i < len(text):
                if text.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif text.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            assert depth == 0, "Unterminated block comment"
        elif c in "'\"" or (c in "Ee" and text[i:i+2].lower() == "e'"):
            escape = c in "Ee"
            q = "'" if escape else c
            start = i
            i += 2 if escape else 1
            while i < len(text):
                if escape and text[i] == "\\":
                    i += 2
                elif text[i] == q:
                    if text[i:i+2] == q * 2:
                        i += 2
                    else:
                        i += 1
                        break
                else:
                    i += 1
            else:
                raise AssertionError("Unterminated quoted value")
            out.append(text[start:i] if q == "'" else text[start+1:i-1])
        elif c == "$" and (m := re.match(r"\$(?:[A-Za-z_]\w*)?\$", text[i:])):
            tag = m.group()
            end = text.find(tag, i + len(tag))
            assert end >= 0, "Unterminated dollar body: " + tag
            body = text[i+len(tag):end]
            bodies.append(lex(body))
            out.append(tag)
            i = end + len(tag)
        elif m := re.match(r"[A-Za-z_]\w*|\d+", text[i:]):
            out.append(m.group())
            i += len(m.group())
        else:
            out.append(c)
            i += 1
    stack = []
    for token in out:
        if token in ("(", "["):
            stack.append(token)
        elif token in (")", "]"):
            assert stack and stack.pop() == {')': '(', ']': '['}[token], "Unbalanced delimiter"
    assert not stack, "Unclosed delimiter"
    return out, bodies


def enclosed(tokens, start):
    assert tokens[start] == "("
    depth = 1
    for end in range(start + 1, len(tokens)):
        depth += (tokens[end] == "(") - (tokens[end] == ")")
        if depth == 0:
            return tokens[start+1:end], end + 1
    raise AssertionError("Unclosed group")


def parts(tokens):
    result, current, depth = [], [], 0
    for token in tokens:
        depth += (token in ("(", "[")) - (token in (")", "]"))
        if token == "," and depth == 0:
            result.append(current)
            current = []
        else:
            current.append(token)
    if current:
        result.append(current)
    return result


def occurrences(tokens, sequence):
    upper = [t.upper() for t in tokens]
    return sum(upper[i:i+len(sequence)] == sequence for i in range(len(upper)))


def all_streams(tree):
    tokens, bodies = tree
    yield tokens
    for body in bodies:
        yield from all_streams(body)


def main():
    text = SQL.read_text(encoding="utf-8")
    tree = lex(text)
    tokens = tree[0]
    upper = [t.upper() for t in tokens]
    assert tokens[:6] == ['BEGIN', ';', 'DO', '$review_stop$', ';', 'SET']
    assert "RAISE EXCEPTION 'REVIEW ONLY: execution requires explicit approval and a new reviewed migration'" in text
    assert tokens[-2:] == ['ROLLBACK', ';']
    assert 'COMMIT' not in upper and 'NOTIFY' not in upper
    assert 'previous_ends_on' not in text
    assert 'enrollment_review_handoff(uuid,uuid,uuid,bigint,bigint,uuid,jsonb)' not in text
    assert not any(line.rstrip() != line for line in text.splitlines())

    inventory, routines = {}, {}
    for i in range(len(tokens) - 5):
        if upper[i:i+3] == ['CREATE', 'TABLE', 'PUBLIC']:
            name = tokens[i+4]
            body, _ = enclosed(tokens, i+5)
            inventory[name] = {
                'checks': occurrences(body, ['CHECK', '(']),
                'fkeys': occurrences(body, ['REFERENCES']),
                'pkeys': occurrences(body, ['PRIMARY', 'KEY']),
                'ukeys': occurrences(body, ['UNIQUE', '(']),
                'xkeys': occurrences(body, ['EXCLUDE']),
                'not_null_columns': occurrences(body, ['NOT', 'NULL']),
                'check_definitions': [' '.join(p) for p in parts(body) if 'CHECK' in p],
            }
        elif upper[i:i+3] == ['CREATE', 'FUNCTION', 'PUBLIC']:
            name = tokens[i+4]
            body, _ = enclosed(tokens, i+5)
            routines[name] = [p[1] for p in parts(body)]
    assert len(inventory) == 4 and len(routines) == 10
    expected = {}
    for m in re.finditer(r"\('(student_\w+)',(\d+),(\d+),(\d+),(\d+),(\d+)\)", text):
        expected[m[1]] = dict(zip(('checks','fkeys','pkeys','ukeys','xkeys'), map(int,m.groups()[1:])))
    assert set(expected) == set(inventory)
    for name, counts in expected.items():
        assert all(inventory[name][key] == val for key,val in counts.items()), (name,counts,inventory[name])
    placement = inventory['student_academic_placements']
    assert placement['checks'] == 8
    assert all('CONSTRAINT enrollment_placement_' in part for part in placement['check_definitions'])

    for name, params in routines.items():
        signature = 'public.' + name + '(' + ','.join(params) + ')'
        assert signature in text, 'Missing postflight signature: ' + signature
    calls = []
    for stream in all_streams(tree):
        for i in range(len(stream) - 3):
            if stream[i:i+2] == ['public', '.'] and stream[i+2] in routines and stream[i+3] == '(':
                args, _ = enclosed(stream, i+3)
                count = len(parts(args))
                assert count == len(routines[stream[i+2]]), (stream[i+2],count)
                calls.append({'routine':stream[i+2], 'arguments':count})

    # Mechanical source probes supplement, but do not replace, the manual report.
    migrations = ROOT / 'supabase/migrations'
    baseline = (migrations/'20250717000000_reconstructed_pre_phase_3_6_baseline.sql').read_text(encoding='utf-8')
    admin = (migrations/'20260909000000_phase_admin_1_admin_student_schema.sql').read_text(encoding='utf-8')
    scoped = (migrations/'20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql').read_text(encoding='utf-8')
    master = (migrations/'20261016000000_academic_master_data_management.sql').read_text(encoding='utf-8')
    convergence = (migrations/'20261016010000_academic_curriculum_semester_convergence.sql').read_text(encoding='utf-8')
    assert '"semester_id" "uuid"' in baseline and '"duration_years" numeric(4,2)' in baseline
    assert '"record_id"       text' in admin and '"record_data"     "jsonb"' in admin
    assert 'COALESCE("auth"."role"(), \'\') <> \'service_role\'' in scoped
    assert '"phase81_admin_audit_append_only"' in scoped
    assert '(pc.semester_id IS NULL OR pc.semester_id=' in master
    assert 'ALTER COLUMN semester_number DROP NOT NULL' in convergence
    preserved = json.loads((HERE/'SOURCE_EVIDENCE.json').read_text(encoding='utf-8'))['files']
    changed = [name for name,sha in preserved.items() if not (ROOT/name).exists() or digest(ROOT/name) != sha]
    assert not changed, changed
    fixtures = json.loads((HERE/'synthetic_fixtures.json').read_text(encoding='utf-8'))
    assert fixtures, 'Missing synthetic fixture specification'
    if (HERE/'SQL_REPAIR_REVIEW.md').exists():
        report = (HERE/'SQL_REPAIR_REVIEW.md').read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)', report):
            if '://' not in target:
                assert (HERE/target.split('#')[0]).exists(), 'Broken report link: '+target
    results = {
        'review_date': '2026-10-11',
        'scope': 'Static text/source review; not PostgreSQL or PL/pgSQL validation',
        'sql_executed': False, 'database_connected': False, 'postgresql_parser_used': False,
        'runtime_tests_run': False, 'docker_invoked': False,
        'checks_passed': ['lexical quote/comment/dollar/delimiter balance','review stop and final ROLLBACK',
            'no COMMIT, NOTIFY, obsolete handoff signature or backdated closure argument',
            'four complete DDL constraint inventories agree with postflight',
            'eight explicitly named placement CHECKs', 'ten routine declarations/signatures/call arities',
            'bounded source contract probes','existing source SHA-256 preservation','fixture JSON loads',
            'report link targets, when report exists','SQL trailing whitespace'],
        'constraint_inventory': inventory, 'postflight_inventory': expected,
        'routine_parameter_types': routines, 'routine_calls_and_declarations': calls,
        'preserved_existing_files':len(preserved), 'changed_existing_files':changed,
        'source_migration_sha256': {p.name:digest(p) for p in sorted(migrations.glob('*.sql'))},
        'sql_sha256_before_repair':digest(HERE/(SQL.name+'.before_repair')),
        'sql_sha256_after_repair':digest(SQL),
        'repair_artifact_sha256':{p.name:digest(p) for p in sorted(HERE.iterdir())
            if p.is_file() and p.name in {SQL.name,'SQL_REPAIR_REVIEW.md','REVIEW_SUMMARY.md','verify_review_static.py'}},
    }
    (HERE/'STATIC_REVIEW_RESULTS.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'static_checks':'passed', 'sql_sha256':digest(SQL),
        'constraint_counts':expected, 'routines':len(routines), 'preserved_existing_files':len(preserved),
        'postgresql_validation':'NOT RUN'},indent=2))


if __name__ == '__main__':
    main()
