"""Build a rollback-only PostgreSQL contract using the actual repair migration.

Execute the generated SQL with `supabase db query --linked --file ...` or psql.
All fixture tables are session-local temporary tables, and all changes roll back.
"""

import argparse
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
MIGRATION = REPOSITORY / "supabase/migrations/20261016010000_academic_curriculum_semester_convergence.sql"


def build_contract() -> str:
    migration = MIGRATION.read_text(encoding="utf-8")
    body = migration.split("BEGIN;", 1)[1].rsplit("COMMIT;", 1)[0]
    body = body.replace("NOTIFY pgrst, 'reload schema';", "")
    body = body.replace("public.program_courses", "pg_temp.program_courses")
    body = body.replace("public.semesters", "pg_temp.semesters")
    legacy = """
BEGIN;
CREATE TEMP TABLE semesters (semester_id uuid PRIMARY KEY);
INSERT INTO pg_temp.semesters VALUES ('40000000-0000-0000-0000-000000000001');
CREATE TEMP TABLE program_courses (
    program_course_id uuid PRIMARY KEY, program_id uuid NOT NULL,
    course_id uuid NOT NULL, course_type text NOT NULL, semester_number integer NOT NULL
);
INSERT INTO pg_temp.program_courses VALUES (
    '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001', 'core', 6
);
"""
    legacy_assertions = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_temp.program_courses WHERE semester_number=6 AND semester_id IS NULL) THEN
        RAISE EXCEPTION 'Legacy curriculum values changed';
    END IF;
    INSERT INTO pg_temp.program_courses(program_course_id,program_id,course_id,course_type)
    VALUES ('10000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001',
        '30000000-0000-0000-0000-000000000002', 'core');
    INSERT INTO pg_temp.program_courses(program_course_id,program_id,course_id,course_type,semester_id)
    VALUES ('10000000-0000-0000-0000-000000000003', '20000000-0000-0000-0000-000000000001',
        '30000000-0000-0000-0000-000000000003', 'core', '40000000-0000-0000-0000-000000000001');
    BEGIN
        INSERT INTO pg_temp.program_courses(program_course_id,program_id,course_id,course_type,semester_id)
        VALUES ('10000000-0000-0000-0000-000000000004', '20000000-0000-0000-0000-000000000001',
            '30000000-0000-0000-0000-000000000004', 'core', '40000000-0000-0000-0000-000000000099');
        RAISE EXCEPTION 'Invalid semester reference accepted';
    EXCEPTION WHEN foreign_key_violation THEN NULL;
    END;
    IF (SELECT count(*) FROM pg_temp.program_courses)<>3 THEN RAISE EXCEPTION 'Unexpected curriculum data changes'; END IF;
END;
$$;
DROP TABLE pg_temp.program_courses;
CREATE TEMP TABLE program_courses (
    program_course_id uuid PRIMARY KEY, program_id uuid NOT NULL,
    course_id uuid NOT NULL, course_type text NOT NULL,
    semester_id uuid CONSTRAINT program_courses_semester_id_fkey REFERENCES pg_temp.semesters(semester_id)
);
INSERT INTO pg_temp.program_courses VALUES (
    '10000000-0000-0000-0000-000000000001', '20000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001', 'core', '40000000-0000-0000-0000-000000000001'
);
"""
    canonical_assertions = """
DO $$
BEGIN
    IF (SELECT count(*) FROM pg_temp.program_courses WHERE semester_id='40000000-0000-0000-0000-000000000001')<>1 THEN
        RAISE EXCEPTION 'Canonical curriculum changed';
    END IF;
    IF (SELECT count(*) FROM pg_catalog.pg_constraint WHERE conrelid='pg_temp.program_courses'::regclass AND contype='f')<>1 THEN
        RAISE EXCEPTION 'Duplicate or missing semester foreign key';
    END IF;
    INSERT INTO pg_temp.program_courses(program_course_id,program_id,course_id,course_type)
    VALUES ('10000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000001',
        '30000000-0000-0000-0000-000000000002', 'elective');
END;
$$;
ROLLBACK;
SELECT 'PASS: legacy and canonical schema, repeated repair, value preservation, optional curriculum and foreign key enforcement' AS convergence_contract;
"""
    return legacy + body + body + legacy_assertions + body + body + canonical_assertions


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_contract(), encoding="utf-8")
    print(f"Rollback-only contract written to {args.output}")
