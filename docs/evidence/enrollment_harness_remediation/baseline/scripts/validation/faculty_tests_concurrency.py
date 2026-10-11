"""Actual assessment races, restricted to the local disposable verifier."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from faculty_attendance_concurrency import CONTAINER, command, literal, sql


def checked(query):
    result = sql(query)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def race(queries):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(sql, queries))
    if sorted(r.returncode for r in results) != [0, 3]:
        raise RuntimeError(str([(r.returncode, r.stderr) for r in results]))
    return results


def main():
    if command(['docker', 'context', 'show']).stdout.strip() != 'desktop-linux':
        raise RuntimeError('Only local Docker Desktop is allowed')
    container = json.loads(command(['docker', 'inspect', CONTAINER], check=True).stdout)[0]
    if container['Mounts'] or container['HostConfig']['PortBindings'] or not container['Config']['Labels'].get('collegeai.attendance-verification'):
        raise RuntimeError('Expected disposable verification container')
    fixture = Path('scripts/validation/faculty_tests_database.sql').read_text()
    seed = fixture[:fixture.index('    t:=save_faculty_test')]
    seed += """    RAISE NOTICE 'EXAM_FIXTURE %',jsonb_build_object('actor',faculty_one,'tenant',tenant,'section',section_one,
       'other',faculty_two,'admin',admin_user,'roster',roster_one,'data',data-'start_time'-'end_time');
END; $$;
COMMIT;
"""
    result = sql(seed)
    if result.returncode:
        raise RuntimeError(result.stderr)
    ctx = json.loads(next(line.split('EXAM_FIXTURE ', 1)[1] for line in result.stderr.splitlines() if 'EXAM_FIXTURE ' in line))
    actor, tenant, section = (literal(ctx[k]) for k in ('actor', 'tenant', 'section'))
    data = literal(json.dumps(ctx['data'])) + '::jsonb'
    create = f'SELECT save_faculty_test({actor},{tenant},{section},{data});'
    results = race([create, create])
    t = json.loads(next(r.stdout.strip() for r in results if r.returncode == 0))
    test = literal(t['test_id'])

    def transition(version, action):
        return f"SELECT transition_faculty_test({actor},{tenant},{test},{version},{literal(action)});"

    checked(transition(1, 'schedule'))
    checked(transition(2, 'complete'))
    rosters = checked(f'SELECT roster_id FROM faculty_attendance_rosters WHERE section_id={section} ORDER BY roster_id;').splitlines()
    rows = literal(json.dumps([{'roster_id': r, 'mark_status': 'present', 'scored_marks': 50} for r in rosters])) + '::jsonb'
    checked(f'SELECT save_faculty_test_marks({actor},{tenant},{test},3,{rows});')
    race([transition(4, 'submit'), transition(4, 'submit')])
    race([transition(5, 'publish'), transition(5, 'publish')])
    mark = f'SELECT save_faculty_test_marks({actor},{tenant},{test},6,{rows});'
    race([transition(6, 'lock'), mark])
    checked(f"DO $$ BEGIN IF (SELECT version FROM faculty_tests WHERE test_id={test})<>7 OR "
            f"(SELECT count(*) FROM admin_audit_log WHERE record_id={test} AND action='test.lock')<>1 "
            "THEN RAISE EXCEPTION 'Duplicate transition or audit'; END IF; END; $$;")
    # A co-teacher and the owner compete; only the owner can update metadata.
    data2 = dict(ctx['data'], title='Import race')
    t2 = json.loads(checked(f'SELECT save_faculty_test({actor},{tenant},{section},{literal(json.dumps(data2))}::jsonb);'))
    test2 = literal(t2['test_id'])
    checked(f"SELECT set_config('request.jwt.claim.role','service_role',false); SELECT create_faculty_teaching_assignment({literal(ctx['admin'])},{tenant},{literal(ctx['other'])},{section},now()-interval '1 day',NULL,true);")
    update = lambda teacher: f'SELECT save_faculty_test({teacher},{tenant},{section},{literal(json.dumps(data2))}::jsonb,{test2},1);'
    race([update(actor), update(literal(ctx['other']))])
    for version, action in [(2, 'schedule'), (3, 'complete')]:
        checked(f"SELECT transition_faculty_test({actor},{tenant},{test2},{version},{literal(action)});")
    register = checked(f"SELECT register_number FROM faculty_attendance_rosters WHERE roster_id={literal(ctx['roster'])};")
    raw = {'register_number': register, 'mark_status': 'present', 'scored_marks': '75'}
    review_rows = [{'row_number': 2, 'raw_data': raw, 'normalized_data': raw, 'validation_status': 'VALID', 'errors': [], 'warnings': []}]
    staged = json.loads(checked(f"SELECT stage_faculty_test_import({actor},{tenant},{test2},'marks.csv','CSV','{{\"valid\":1}}'," + literal(json.dumps(review_rows)) + '::jsonb);'))
    imported = literal(staged['import_id'])
    stamp = checked(f'SELECT updated_at FROM faculty_attendance_imports WHERE import_id={imported};')
    commit = f'SELECT commit_faculty_test_import({actor},{tenant},{imported},{literal(stamp)},4);'
    race([commit, commit])
    checked(f"DO $$ BEGIN IF (SELECT count(*) FROM test_results WHERE test_id={test2})<>1 OR "
            f"(SELECT count(*) FROM admin_audit_log WHERE record_id={test2} AND action='test.import.commit')<>1 "
            "THEN RAISE EXCEPTION 'Duplicate import records/audits'; END IF; END; $$;")
    # Live authorization is rechecked after waiting on the same roster lock.
    holder = subprocess.Popen(['docker', 'exec', '-i', CONTAINER, 'psql', '-U', 'postgres', '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-At'],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    holder.stdin.write(f"BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('attendance:'||{tenant}::text,0)); "
                       f"UPDATE faculty_section_assignments SET revoked_at=now(),revoked_by={literal(ctx['admin'])} WHERE faculty_user_id={actor} AND institution_id={tenant}; "
                       "SELECT 'LOCK_HELD'; SELECT pg_sleep(2); COMMIT;\n")
    holder.stdin.flush()
    while 'LOCK_HELD' not in holder.stdout.readline():
        if holder.poll() is not None:
            raise RuntimeError('Lock holder failed')
    denied = sql(f'SELECT save_faculty_test_marks({actor},{tenant},{test2},5,{rows});')
    holder.communicate(timeout=15)
    if holder.returncode or denied.returncode != 3 or 'Teaching mutation denied' not in denied.stderr:
        raise RuntimeError('Waiting assessment write did not recheck revocation')
    print('PASS: duplicate creation, co-teacher ownership, simultaneous submit/publish/lock, marks versus lock, import commit, audits and revocation after wait')


if __name__ == '__main__':
    main()
