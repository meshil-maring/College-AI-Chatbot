"""Real concurrent writes, restricted to the disposable attendance container.

Run from the repository root after all migrations. Seeds only that disposable
container; never accepts a remote URL, credential, or arbitrary database name.
"""
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CONTAINER = 'codex-attendance-verify-20261007'


def command(args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, timeout=60, **kwargs)


def sql(query):
    return command(['docker', 'exec', '-i', CONTAINER, 'psql', '-U', 'postgres', '-d', 'postgres',
                    '-v', 'ON_ERROR_STOP=1', '-At'], input=query)


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def main():
    if command(['docker', 'context', 'show']).stdout.strip() != 'desktop-linux':
        raise RuntimeError('Only local Docker Desktop is allowed')
    container = json.loads(command(['docker', 'inspect', CONTAINER], check=True).stdout)[0]
    if container['Config']['Image'] != 'public.ecr.aws/supabase/postgres:17.6.1.166' or container['Mounts'] or container['HostConfig']['PortBindings']:
        raise RuntimeError('Expected disposable container without mounts or host ports')
    fixture = Path('scripts/validation/faculty_attendance_database.sql').read_text(encoding='utf-8')
    seed = fixture[:fixture.index('    PERFORM commit_faculty_attendance_import')]
    seed += """    RAISE NOTICE 'ATTENDANCE_FIXTURE %', jsonb_build_object('tenant',tenant,'actor',faculty_one,
        'admin',admin_user,'section',section_one,'import',attendance_import_id,'version',version,'rows',rows);
END; $$;
COMMIT;
"""
    result = sql(seed)
    if result.returncode: raise RuntimeError(result.stderr)
    context = json.loads(next(line.split('ATTENDANCE_FIXTURE ', 1)[1] for line in result.stderr.splitlines() if 'ATTENDANCE_FIXTURE ' in line))
    actor, tenant, section = (literal(context[k]) for k in ('actor', 'tenant', 'section'))
    commit = 'SELECT commit_faculty_attendance_import(' + ','.join([
        actor, tenant, literal(context['import']), literal(context['version']), literal(json.dumps(context['rows'])) + '::jsonb']) + ');'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(sql, [commit, commit]))
    if sorted(r.returncode for r in results) != [0, 3] or not any('already committed' in r.stderr for r in results):
        raise RuntimeError('Concurrent duplicate commit did not allow exactly one transaction: ' + str([(r.returncode, r.stderr) for r in results]))
    row = sql(f"SELECT roster_id FROM faculty_attendance_rosters WHERE institution_id={tenant} AND register_number={literal(context['rows'][0]['normalized_data']['register_number'])};").stdout.strip()
    if not row: raise RuntimeError('Committed roster missing')
    mark = f"SELECT mark_faculty_attendance({actor},{tenant},{section},'2026-10-08'," + literal(json.dumps({row: 'present'})) + '::jsonb);'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(sql, [mark, mark]))
    if any(r.returncode for r in results): raise RuntimeError('Concurrent same-owner marking failed')
    check = sql(f"SELECT count(*) FROM faculty_attendance_sessions WHERE section_id={section} AND session_date='2026-10-08'; SELECT count(*) FROM faculty_attendance_records WHERE roster_id='{row}'; SELECT count(*) FROM admin_audit_log WHERE institution_id={tenant} AND action='attendance.import.commit';")
    if check.stdout.strip().splitlines() != ['1', '2', '1']: raise RuntimeError('Concurrent writes produced duplicate sessions, records or commits')
    # A request waiting on the transaction lock must observe committed revocation.
    holder = subprocess.Popen(['docker','exec','-i',CONTAINER,'psql','-U','postgres','-d','postgres','-v','ON_ERROR_STOP=1','-At'],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    holder.stdin.write(f"BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('attendance:' || {tenant}::text,0)); UPDATE faculty_section_assignments SET revoked_at=now(),revoked_by={literal(context['admin'])} WHERE institution_id={tenant} AND faculty_user_id={actor}; SELECT 'LOCK_HELD'; SELECT pg_sleep(2); COMMIT;\n")
    holder.stdin.flush()
    while 'LOCK_HELD' not in holder.stdout.readline():
        if holder.poll() is not None: raise RuntimeError('Revocation lock holder failed')
    denied = sql(mark)
    holder.communicate(timeout=15)
    if holder.returncode or denied.returncode != 3 or 'Teaching mutation denied' not in denied.stderr:
        raise RuntimeError('A waiting request did not observe revocation')
    print('PASS: concurrent import commit, same-owner marking, uniqueness, atomic audit, and revocation recheck')


if __name__ == '__main__':
    main()
