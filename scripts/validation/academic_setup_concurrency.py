"""Academic duplicate races, restricted to the disposable verification container."""

import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

container = sys.argv[1]
if not container.startswith("codex-academic-setup-"):
    raise SystemExit("Only an academic setup verification container is allowed")
label = subprocess.run(["docker", "inspect", "--format", '{{ index .Config.Labels "collegeai.academic-setup-verification" }}', container], capture_output=True, text=True, check=True).stdout.strip()
if label != "true":
    raise SystemExit("Disposable container label required")


def sql(query):
    return subprocess.run(["docker", "exec", "-i", container, "psql", "-U", "postgres", "-d", "postgres", "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=verbose", "-At"], input=query, capture_output=True, text=True, timeout=40)


def checked(query):
    result = sql(query)
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


org, tenant, a, b, dept, program, year, semester, course, offering = [str(uuid4()) for _ in range(10)]
checked(f"""
BEGIN;
INSERT INTO organizations(organization_id,name,organization_code,official_email,contact_information,status) VALUES('{org}','Isolated race','AS-{org}','race@example.invalid','Disposable','active');
INSERT INTO institutions(institution_id,name,code,organization_id,status) VALUES('{tenant}','Isolated race','AS-{tenant}','{org}','active');
INSERT INTO auth.users(id,email) VALUES('{a}','{a}@example.invalid'),('{b}','{b}@example.invalid');
INSERT INTO users(id,auth_user_id,email,first_name,last_name) SELECT id,id,email,'Race','Admin' FROM auth.users WHERE id IN('{a}','{b}');
INSERT INTO user_roles(user_id,role_id,scope_type,scope_id,scope_organization_id) SELECT u.id,r.id,'institution','{tenant}','{org}' FROM (VALUES('{a}'::uuid),('{b}'::uuid)) u(id) CROSS JOIN roles r WHERE r.name='admin';
INSERT INTO departments(department_id,institution_id,name,code) VALUES('{dept}','{tenant}','Race parent','PARENT');
INSERT INTO programs(program_id,department_id,name,code,degree_type,duration_years) VALUES('{program}','{dept}','Race parent','PARENT','BSc',3);
INSERT INTO academic_years(academic_year_id,institution_id,name,code,start_date,end_date) VALUES('{year}','{tenant}','2026-27','Y26','2026-07-01','2027-06-30');
INSERT INTO semesters(semester_id,academic_year_id,name,code,semester_number,start_date,end_date) VALUES('{semester}','{year}','Semester 1','S1',1,'2026-07-01','2026-12-31');
INSERT INTO courses(course_id,department_id,name,code) VALUES('{course}','{dept}','Race subject','SUBJECT');
INSERT INTO program_courses(program_id,course_id,course_type) VALUES('{program}','{course}','core');
COMMIT;
""")


def race(entity, payloads, expected="23505"):
    barrier = threading.Barrier(2)
    def worker(pair):
        actor, payload = pair
        barrier.wait()
        return sql("BEGIN; SELECT set_config('request.jwt.claim.role','service_role',true); SELECT manage_academic_master_record(" + ",".join([quote(actor), quote(tenant), quote(entity), "NULL", quote(json.dumps(payload)) + "::jsonb"]) + "); SELECT pg_sleep(0.4); COMMIT;")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, zip([a, b], payloads)))
    if sorted(result.returncode for result in results) != [0, 3]:
        raise RuntimeError(f"{entity}: wrong race outcomes: {[r.stderr for r in results]}")
    failure = next(result for result in results if result.returncode)
    if expected not in failure.stderr:
        raise RuntimeError(f"{entity}: unexpected error {failure.stderr}")
    count = checked(f"SELECT count(*) FROM admin_audit_log WHERE institution_id='{tenant}' AND action='academic.{entity}.create';")
    if count != "1":
        raise RuntimeError(f"{entity}: successful create was not audited exactly once")
    print(f"PASS: concurrent {entity} creates: one commit, one {expected}; one audit")


race("departments", [{"name": "Race department", "code": "RACE"}, {"name": "Race department", "code": " race "}])
race("programs", [{"department_id": dept, "name": "Race program", "code": code, "degree_type": "BSc", "duration_years": 3} for code in ["RACE", "race"]])
payload = {"program_id": program, "course_id": course, "academic_year_id": year, "semester_id": semester}
race("course_offerings", [payload, payload])
offering = checked(f"SELECT course_offering_id FROM course_offerings WHERE program_id='{program}';")
race("sections", [{"course_offering_id": offering, "name": "Section A", "code": code} for code in ["A", " a "]])
race("academic_years", [{"name": "Next year", "code": code, "start_date": "2027-07-01", "end_date": "2028-06-30"} for code in ["Y27A", "Y27B"]], "23P01")
print("ACADEMIC CONCURRENCY PASS: five races in disposable database; no remote or persistent fixtures")
