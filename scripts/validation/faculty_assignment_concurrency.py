"""Exercise scoped teaching-assignment races against the local Supabase database."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

CONTAINER = "supabase_db_CollegeAIChatbot"
IMAGE = "public.ecr.aws/supabase/postgres:17.6.1.166"


def command(args, **kwargs):
    return subprocess.run(args, capture_output=True, text=True, timeout=60, **kwargs)


def sql(query):
    return command(
        [
            "docker",
            "exec",
            "-i",
            CONTAINER,
            "psql",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-v",
            "ON_ERROR_STOP=1",
            "-At",
        ],
        input=query,
    )


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def checked(query):
    result = sql(query)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def race(queries):
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(pool.map(sql, queries))


def scoped_call(actor, tenant, faculty, section, start, end, active, revoke=False, assignment=None):
    return (
        "SELECT manage_scoped_faculty_teaching_assignment("
        + ",".join(
            [
                literal(actor),
                literal(tenant),
                literal(assignment) if assignment else "NULL",
                literal(faculty) if faculty else "NULL",
                literal(section) if section else "NULL",
                start or "NULL",
                end or "NULL",
                str(active).lower(),
                str(revoke).lower(),
            ]
        )
        + ");"
    )


def expect_one_success_one_failure(results, expected_error):
    if sorted(result.returncode for result in results) != [0, 3]:
        raise RuntimeError(f"Expected one commit and one rejection: {[(r.returncode, r.stderr) for r in results]}")
    rejected = next(result for result in results if result.returncode)
    if expected_error not in rejected.stderr:
        raise RuntimeError(f"Expected {expected_error!r}, got {rejected.stderr}")
    return next(result for result in results if not result.returncode).stdout.strip().splitlines()[-1]


def wait_for_marker(process, marker):
    while True:
        line = process.stdout.readline()
        if marker in line:
            return
        if process.poll() is not None:
            raise RuntimeError(f"Lock-holder exited before {marker}: {process.stderr.read()}")


def main():
    context = command(["docker", "context", "show"])
    if context.returncode or context.stdout.strip() != "desktop-linux":
        raise RuntimeError("Only Docker Desktop's local Supabase database is allowed")
    inspected = json.loads(command(["docker", "inspect", CONTAINER], check=True).stdout)[0]
    bindings = inspected["NetworkSettings"]["Ports"].get("5432/tcp") or []
    if inspected["Config"]["Image"] != IMAGE or not any(binding.get("HostPort") == "54322" for binding in bindings):
        raise RuntimeError("Expected the project's local Supabase PostgreSQL container")

    fixture = r"""
BEGIN;
SET LOCAL search_path = public, extensions;
SELECT set_config('request.jwt.claim.role', 'service_role', true);
DO $$
DECLARE
    org uuid := gen_random_uuid(); tenant uuid := gen_random_uuid();
    admin_user uuid := gen_random_uuid(); manager_hod uuid := gen_random_uuid();
    manager_program uuid := gen_random_uuid(); manager_course uuid := gen_random_uuid();
    faculty_a uuid := gen_random_uuid(); faculty_b uuid := gen_random_uuid();
    dept uuid := gen_random_uuid(); math_dept uuid := gen_random_uuid();
    program uuid := gen_random_uuid(); year_id uuid := gen_random_uuid();
    semester uuid := gen_random_uuid(); course_one uuid := gen_random_uuid();
    course_two uuid := gen_random_uuid(); offering_one uuid := gen_random_uuid();
    offering_two uuid := gen_random_uuid(); section_one uuid := gen_random_uuid();
    section_two uuid := gen_random_uuid(); roster uuid := gen_random_uuid();
    hod_id uuid; program_id uuid; course_id uuid; assignment_id uuid;
    suffix text := upper(substr(gen_random_uuid()::text, 1, 8));
BEGIN
    INSERT INTO organizations(organization_id, name, organization_code, official_email, contact_information, status)
    VALUES(org, 'Assignment race verification', 'AR-' || suffix, 'race@example.invalid', 'Local fixture', 'active');
    INSERT INTO institutions(institution_id, name, code, organization_id, status)
    VALUES(tenant, 'Assignment race verification', 'ARI-' || suffix, org, 'active');
    INSERT INTO auth.users(id, email) VALUES
        (admin_user, admin_user || '@example.invalid'),
        (manager_hod, manager_hod || '@example.invalid'),
        (manager_program, manager_program || '@example.invalid'),
        (manager_course, manager_course || '@example.invalid'),
        (faculty_a, faculty_a || '@example.invalid'),
        (faculty_b, faculty_b || '@example.invalid');
    INSERT INTO users(id, auth_user_id, email, first_name, last_name)
    SELECT id, id, email, 'Race', 'Fixture' FROM auth.users
    WHERE id IN (admin_user, manager_hod, manager_program, manager_course, faculty_a, faculty_b);
    INSERT INTO user_roles(user_id, role_id, scope_type, scope_id, scope_organization_id)
    SELECT admin_user, id, 'institution', tenant, org FROM roles WHERE name = 'admin';
    INSERT INTO user_roles(user_id, role_id, scope_type, scope_id, scope_organization_id)
    SELECT person.id, role.id, 'institution', tenant, org
    FROM (VALUES(manager_hod), (manager_program), (manager_course), (faculty_a), (faculty_b)) AS person(id)
    CROSS JOIN roles AS role WHERE role.name = 'faculty';
    INSERT INTO departments(department_id, institution_id, name, code) VALUES
        (dept, tenant, 'Computer Science', 'CS-' || suffix),
        (math_dept, tenant, 'Mathematics', 'MA-' || suffix);
    INSERT INTO programs(program_id, department_id, name, code, degree_type, duration_years)
    VALUES(program, dept, 'B.Tech', 'BT-' || suffix, 'B.Tech', 4);
    INSERT INTO academic_years(academic_year_id, institution_id, name, code, start_date, end_date)
    VALUES(year_id, tenant, '2026-27', 'AY-' || suffix, '2026-07-01', '2027-06-30');
    INSERT INTO semesters(semester_id, academic_year_id, name, code, semester_number, start_date, end_date)
    VALUES(semester, year_id, 'Semester 5', 'S5-' || suffix, 5, '2026-07-01', '2026-12-31');
    INSERT INTO courses(course_id, department_id, name, code) VALUES
        (course_one, dept, 'Data Mining', 'DM-' || suffix),
        (course_two, math_dept, 'Mathematics', 'MT-' || suffix);
    INSERT INTO program_courses(program_id, course_id, course_type) VALUES
        (program, course_one, 'core'), (program, course_two, 'elective');
    INSERT INTO course_offerings(course_offering_id, course_id, program_id, academic_year_id, semester_id)
    VALUES(offering_one, course_one, program, year_id, semester),
          (offering_two, course_two, program, year_id, semester);
    INSERT INTO sections(section_id, course_offering_id, name, code) VALUES
        (section_one, offering_one, 'Section A', 'A'),
        (section_two, offering_two, 'Section A', 'A');
    hod_id := manage_faculty_responsibility(admin_user, tenant, manager_hod, 'hod', 'department', dept,
        now() - interval '1 day', NULL, true);
    program_id := manage_faculty_responsibility(admin_user, tenant, manager_program, 'program_coordinator',
        'program', program, now() - interval '1 day', NULL, true);
    course_id := manage_faculty_responsibility(admin_user, tenant, manager_course, 'course_coordinator',
        'course', course_one, now() - interval '1 day', NULL, true);
    assignment_id := create_faculty_teaching_assignment(admin_user, tenant, faculty_a, section_two,
        now() - interval '1 day', NULL, true);
    INSERT INTO faculty_attendance_rosters(roster_id, institution_id, section_id, course_offering_id,
        semester_id, register_number, university_roll_number, student_name, created_by)
    VALUES(roster, tenant, section_two, offering_two, semester, 'R-' || suffix, 'U-' || suffix,
        'Concurrency fixture', faculty_a);
    RAISE NOTICE 'ASSIGNMENT_FIXTURE %', jsonb_build_object(
        'tenant', tenant, 'admin', admin_user, 'manager_hod', manager_hod,
        'manager_program', manager_program, 'manager_course', manager_course,
        'faculty_a', faculty_a, 'faculty_b', faculty_b, 'section_one', section_one,
        'section_two', section_two, 'course_one', course_one, 'roster', roster,
        'course_responsibility', course_id, 'mutation_assignment', assignment_id);
END; $$;
COMMIT;
"""
    seeded = sql(fixture)
    if seeded.returncode:
        raise RuntimeError(seeded.stderr)
    marker = next(
        line.split("ASSIGNMENT_FIXTURE ", 1)[1]
        for line in seeded.stderr.splitlines()
        if "ASSIGNMENT_FIXTURE " in line
    )
    ctx = json.loads(marker)
    tenant = literal(ctx["tenant"])
    base = "SELECT set_config('request.jwt.claim.role','service_role',false); "

    def create(actor, faculty, section, start="now() - interval '1 day'", end="NULL"):
        return base + scoped_call(actor, ctx["tenant"], faculty, section, start, end, True)

    create_race = race(
        [
            "SELECT pg_sleep(0.2); " + create(ctx["manager_hod"], ctx["faculty_a"], ctx["section_one"]),
            "SELECT pg_sleep(0.2); " + create(ctx["manager_program"], ctx["faculty_a"], ctx["section_one"]),
        ]
    )
    created_id = expect_one_success_one_failure(create_race, "uq_faculty_section_assignments_active")
    duplicate_count = checked(
        f"SELECT count(*) FROM faculty_section_assignments WHERE institution_id={tenant} "
        f"AND faculty_user_id={literal(ctx['faculty_a'])} AND section_id={literal(ctx['section_one'])} AND revoked_at IS NULL;"
    )
    if duplicate_count != "1" or checked(
        f"SELECT count(*) FROM admin_audit_log WHERE institution_id={tenant} "
        f"AND record_id={literal(created_id)} AND action='faculty.assignment.assign';"
    ) != "1":
        raise RuntimeError("Duplicate create race left inconsistent assignment or audit state")

    checked(
        base
        + scoped_call(
            ctx["manager_hod"], ctx["tenant"], None, None, None, None, False, True, created_id
        )
    )
    conflict_race = race(
        [
            "SELECT pg_sleep(0.2); "
            + create(
                ctx["manager_hod"],
                ctx["faculty_a"],
                ctx["section_one"],
                "now() - interval '4 days'",
                "now() - interval '3 days'",
            ),
            "SELECT pg_sleep(0.2); "
            + create(
                ctx["manager_program"],
                ctx["faculty_a"],
                ctx["section_one"],
                "now() + interval '3 days'",
                "now() + interval '4 days'",
            ),
        ]
    )
    conflict_id = expect_one_success_one_failure(conflict_race, "uq_faculty_section_assignments_active")
    if checked(
        f"SELECT count(*) FROM faculty_section_assignments WHERE institution_id={tenant} "
        f"AND faculty_user_id={literal(ctx['faculty_a'])} AND section_id={literal(ctx['section_one'])} AND revoked_at IS NULL;"
    ) != "1" or checked(
        f"SELECT count(*) FROM admin_audit_log WHERE institution_id={tenant} "
        f"AND record_id={literal(conflict_id)} AND action='faculty.assignment.assign';"
    ) != "1":
        raise RuntimeError("Non-overlapping validity windows bypassed the one-unrevoked-assignment rule")
    checked(
        base
        + scoped_call(
            ctx["manager_program"], ctx["tenant"], None, None, None, None, False, True, conflict_id
        )
    )

    revoke = subprocess.Popen(
        [
            "docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "postgres",
            "-v", "ON_ERROR_STOP=1", "-At",
        ],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    revoke.stdin.write(
        "BEGIN; "
        + base
        + scoped_call(
            ctx["manager_program"], ctx["tenant"], None, None, None, None, False, True,
            ctx["mutation_assignment"],
        )
        + " SELECT 'REVOKED_HELD'; SELECT pg_sleep(1); COMMIT;\n"
    )
    revoke.stdin.flush()
    wait_for_marker(revoke, "REVOKED_HELD")
    mutation = sql(
        base
        + f"SELECT mark_faculty_attendance({literal(ctx['faculty_a'])},{tenant},"
        + f"{literal(ctx['section_two'])},current_date + 1,"
        + f"jsonb_build_object({literal(ctx['roster'])},'present'));"
    )
    revoke.communicate(timeout=15)
    if revoke.returncode or mutation.returncode != 3 or "Teaching mutation denied" not in mutation.stderr:
        raise RuntimeError("Attendance mutation was not denied after the concurrent assignment revoke")
    if checked(
        f"SELECT count(*) FROM faculty_attendance_sessions WHERE section_id={literal(ctx['section_two'])} "
        "AND session_date=current_date + 1;"
    ) != "0":
        raise RuntimeError("Revoked assignment produced an attendance session")

    assignment_id = checked(
        base
        + scoped_call(
            ctx["manager_program"], ctx["tenant"], ctx["faculty_b"], ctx["section_one"],
            "now() - interval '1 day'", "NULL", True,
        )
    ).splitlines()[-1]
    update = (
        "SELECT pg_sleep(0.2); "
        + base
        + scoped_call(
            ctx["manager_hod"], ctx["tenant"], None, None, "now() - interval '2 days'",
            "NULL", True, False, assignment_id,
        )
    )
    revoke_assignment = (
        "SELECT pg_sleep(0.2); "
        + base
        + scoped_call(
            ctx["manager_program"], ctx["tenant"], None, None, None, None, False, True, assignment_id
        )
    )
    update_results, revoke_results = race([update, revoke_assignment])
    if revoke_results.returncode:
        raise RuntimeError(f"Concurrent revoke failed: {revoke_results.stderr}")
    if update_results.returncode and "Teaching assignment not found" not in update_results.stderr:
        raise RuntimeError(f"Concurrent update failed unexpectedly: {update_results.stderr}")
    if checked(
        f"SELECT count(*) FROM faculty_section_assignments WHERE assignment_id={literal(assignment_id)} "
        "AND revoked_at IS NOT NULL AND is_active=false;"
    ) != "1":
        raise RuntimeError("Update-versus-revoke race did not leave the assignment revoked")
    if checked(
        f"SELECT count(*) FROM admin_audit_log WHERE institution_id={tenant} "
        f"AND record_id={literal(assignment_id)} AND action='faculty.assignment.revoke';"
    ) != "1":
        raise RuntimeError("Update-versus-revoke race has missing or duplicate revoke audit")

    revoke_responsibility = subprocess.Popen(
        [
            "docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "postgres",
            "-v", "ON_ERROR_STOP=1", "-At",
        ],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    revoke_responsibility.stdin.write(
        "BEGIN; "
        + base
        + "SELECT manage_faculty_responsibility("
        + ",".join(
            [
                literal(ctx["admin"]), tenant, literal(ctx["manager_course"]),
                "'course_coordinator'", "'course'", literal(ctx["course_one"]),
                "NULL", "NULL", "false", literal(ctx["course_responsibility"]), "true",
            ]
        )
        + "); SELECT 'RESPONSIBILITY_REVOKED_HELD'; SELECT pg_sleep(1); COMMIT;\n"
    )
    revoke_responsibility.stdin.flush()
    wait_for_marker(revoke_responsibility, "RESPONSIBILITY_REVOKED_HELD")
    scoped_attempt = sql(
        base + create(ctx["manager_course"], ctx["faculty_b"], ctx["section_one"])
    )
    revoke_responsibility.communicate(timeout=15)
    if (
        revoke_responsibility.returncode
        or scoped_attempt.returncode != 3
        or "Active scoped assignment-management responsibility required" not in scoped_attempt.stderr
    ):
        raise RuntimeError("Responsibility revocation raced into a scoped privilege escalation")
    if checked(
        f"SELECT count(*) FROM faculty_section_assignments WHERE institution_id={tenant} "
        f"AND faculty_user_id={literal(ctx['faculty_b'])} AND section_id={literal(ctx['section_one'])} "
        "AND revoked_at IS NULL;"
    ) != "0":
        raise RuntimeError("Revoked coordinator created an assignment outside the authorized state")
    if checked(
        f"SELECT count(*) FROM admin_audit_log WHERE institution_id={tenant} "
        f"AND actor_user_id={literal(ctx['manager_course'])} "
        "AND action='faculty.assignment.assign';"
    ) != "0":
        raise RuntimeError("Denied scoped assignment attempt emitted a success audit")

    print(
        "PASS: concurrent duplicate and non-overlapping-validity conflicts; "
        "revoke versus attendance mutation; update versus revoke; "
        "responsibility revoke versus scoped create; consistency and audit checks"
    )


if __name__ == "__main__":
    main()
