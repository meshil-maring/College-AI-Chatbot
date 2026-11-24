-- Academic Setup database rules, exercised on a real Postgres.
-- Run against the local stack only: `supabase test db` (never --linked).
-- Everything runs in one transaction and is rolled back.
BEGIN;
CREATE EXTENSION IF NOT EXISTS pgtap WITH SCHEMA extensions;
SET LOCAL search_path = public, extensions;
SELECT plan(17);

-- Fixture: one active institution with a published B.Tech curriculum, a 2026
-- batch, Section A (capacity 60) and one subject offering (capacity 40).
INSERT INTO organizations (organization_id, name, organization_code, official_email, contact_information)
VALUES ('00000000-0000-4000-8000-000000000001', 'Test Org', 'TORG', 'org@example.test', 'n/a');
UPDATE organizations SET status = 'active' WHERE organization_id = '00000000-0000-4000-8000-000000000001';
INSERT INTO institutions (institution_id, name, code, organization_id) VALUES
    ('00000000-0000-4000-8000-000000000002', 'Test College', 'TCOL', '00000000-0000-4000-8000-000000000001'),
    ('00000000-0000-4000-8000-0000000000f2', 'Other College', 'OCOL', '00000000-0000-4000-8000-000000000001');
UPDATE institutions SET status = 'active' WHERE organization_id = '00000000-0000-4000-8000-000000000001';
INSERT INTO departments (department_id, institution_id, name, code)
VALUES ('00000000-0000-4000-8000-000000000003', '00000000-0000-4000-8000-000000000002', 'CSE', 'CSE');
INSERT INTO programs (program_id, department_id, name, code, degree_type, duration_years)
VALUES ('00000000-0000-4000-8000-000000000004', '00000000-0000-4000-8000-000000000003', 'B.Tech', 'BT', 'B.Tech', 4);
INSERT INTO academic_years (academic_year_id, institution_id, name, code, start_date, end_date) VALUES
    ('00000000-0000-4000-8000-000000000005', '00000000-0000-4000-8000-000000000002', '2026-27', 'AY26', '2026-08-01', '2027-07-31'),
    ('00000000-0000-4000-8000-000000000015', '00000000-0000-4000-8000-000000000002', '2031-32', 'AY31', '2031-08-01', '2032-07-31');
INSERT INTO semesters (semester_id, academic_year_id, name, code, semester_number, start_date, end_date) VALUES
    ('00000000-0000-4000-8000-000000000006', '00000000-0000-4000-8000-000000000005', 'Odd', 'ODD26', 1, '2026-08-01', '2027-01-29'),
    ('00000000-0000-4000-8000-000000000016', '00000000-0000-4000-8000-000000000015', 'Odd', 'ODD31', 1, '2031-08-01', '2032-01-29');
INSERT INTO courses (course_id, department_id, name, code, credits)
VALUES ('00000000-0000-4000-8000-000000000007', '00000000-0000-4000-8000-000000000003', 'Programming', 'CS101', 1.5);
INSERT INTO program_semesters (program_semester_id, institution_id, program_id, name, code, semester_number) VALUES
    ('00000000-0000-4000-8000-000000000008', '00000000-0000-4000-8000-000000000002',
     '00000000-0000-4000-8000-000000000004', 'Semester 1', 'SEM-1', 1),
    ('00000000-0000-4000-8000-000000000018', '00000000-0000-4000-8000-000000000002',
     '00000000-0000-4000-8000-000000000004', 'Semester 2', 'SEM-2', 2);
INSERT INTO curriculum_versions (curriculum_version_id, institution_id, program_id, academic_year_id, name, version, total_semesters) VALUES
    ('00000000-0000-4000-8000-000000000009', '00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-000000000004',
     '00000000-0000-4000-8000-000000000005', 'BT 2026', '1.0', 8),
    ('00000000-0000-4000-8000-000000000019', '00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-000000000004',
     '00000000-0000-4000-8000-000000000005', 'BT 2026 empty', '2.0', 8);
INSERT INTO curriculum_subjects (curriculum_subject_id, institution_id, curriculum_version_id, program_semester_id, course_id)
VALUES ('00000000-0000-4000-8000-00000000000a', '00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-000000000009',
        '00000000-0000-4000-8000-000000000008', '00000000-0000-4000-8000-000000000007');
UPDATE curriculum_versions SET status = 'published' WHERE curriculum_version_id = '00000000-0000-4000-8000-000000000009';
INSERT INTO admission_cohorts (admission_cohort_id, institution_id, program_id, curriculum_version_id, academic_year_id, name, code, start_year, end_year)
VALUES ('00000000-0000-4000-8000-00000000000b', '00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-000000000004',
        '00000000-0000-4000-8000-000000000009', '00000000-0000-4000-8000-000000000005', 'CSE 2026', 'CSE26', 2026, 2030);
INSERT INTO academic_sections (academic_section_id, institution_id, admission_cohort_id, program_semester_id, semester_id, name, code, capacity)
VALUES ('00000000-0000-4000-8000-00000000000c', '00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-00000000000b',
        '00000000-0000-4000-8000-000000000008', '00000000-0000-4000-8000-000000000006', 'Section A', 'A', 60);
INSERT INTO academic_offerings (academic_offering_id, institution_id, academic_section_id, curriculum_subject_id, capacity)
VALUES ('00000000-0000-4000-8000-00000000000d', '00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-00000000000c',
        '00000000-0000-4000-8000-00000000000a', 40);

-- Published curricula
SELECT is((SELECT credits FROM curriculum_subjects WHERE curriculum_subject_id = '00000000-0000-4000-8000-00000000000a'),
          1.50::numeric, 'publishing keeps a fractional credit snapshot exactly');
SELECT throws_ok($$UPDATE curriculum_versions SET status = 'published'
                   WHERE curriculum_version_id = '00000000-0000-4000-8000-000000000019'$$,
                 '23514', 'An active mapped subject is required before publication',
                 'an empty draft cannot be published');
SELECT throws_ok($$UPDATE curriculum_subjects SET course_type = 'elective'
                   WHERE curriculum_subject_id = '00000000-0000-4000-8000-00000000000a'$$,
                 '23514', 'Published curriculum mappings are immutable',
                 'published subject mappings cannot change');

-- Batch years
SELECT throws_ok($$INSERT INTO admission_cohorts (institution_id, program_id, curriculum_version_id, academic_year_id, name, code, start_year, end_year)
                   VALUES ('00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-000000000004', '00000000-0000-4000-8000-000000000009',
                           '00000000-0000-4000-8000-000000000005', 'Wrong start', 'WS', 2027, 2031)$$,
                 '23514', 'Batch start year must match its intake academic year',
                 'a batch must start in its intake academic year');
SELECT throws_ok($$INSERT INTO admission_cohorts (institution_id, program_id, curriculum_version_id, academic_year_id, name, code, start_year, end_year)
                   VALUES ('00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-000000000004', '00000000-0000-4000-8000-000000000009',
                           '00000000-0000-4000-8000-000000000005', 'Too long', 'TL', 2026, 2031)$$,
                 '23514', 'Batch cannot run longer than its program duration',
                 'a batch cannot outlast its program');
SELECT lives_ok($$INSERT INTO admission_cohorts (institution_id, program_id, curriculum_version_id, academic_year_id, name, code, start_year, end_year)
                  VALUES ('00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-000000000004', '00000000-0000-4000-8000-000000000009',
                          '00000000-0000-4000-8000-000000000005', 'Lateral', 'LAT', 2026, 2029)$$,
                'a shorter lateral-entry batch is allowed');

-- Sections and offerings
SELECT throws_ok($$INSERT INTO academic_sections (institution_id, admission_cohort_id, program_semester_id, semester_id, name, code)
                   VALUES ('00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-00000000000b',
                           '00000000-0000-4000-8000-000000000008', '00000000-0000-4000-8000-000000000016', 'Late', 'LATE')$$,
                 '23514', 'Section teaching term must fall within its batch years',
                 'a section term must fall within its batch years');
SELECT throws_ok($$UPDATE academic_offerings SET capacity = 70
                   WHERE academic_offering_id = '00000000-0000-4000-8000-00000000000d'$$,
                 '23514', 'Offering capacity cannot exceed its section capacity',
                 'an offering cannot hold more than its section');
SELECT throws_ok($$UPDATE academic_sections SET capacity = 30
                   WHERE academic_section_id = '00000000-0000-4000-8000-00000000000c'$$,
                 '23514', 'Section capacity is below a subject offering capacity',
                 'a section cannot shrink below an active offering');
SELECT lives_ok($$UPDATE academic_sections SET capacity = 40
                  WHERE academic_section_id = '00000000-0000-4000-8000-00000000000c'$$,
                'a section can shrink down to its largest offering');
SELECT lives_ok($$UPDATE academic_offerings SET is_active = false, capacity = 55
                  WHERE academic_offering_id = '00000000-0000-4000-8000-00000000000d'$$,
                'an inactive offering is not limited by section capacity changes');

-- Section codes are unique per batch and program semester, not per institution
SELECT lives_ok($$INSERT INTO academic_sections (institution_id, admission_cohort_id, program_semester_id, semester_id, name, code)
                  SELECT '00000000-0000-4000-8000-000000000002', admission_cohort_id,
                         '00000000-0000-4000-8000-000000000008', '00000000-0000-4000-8000-000000000006', 'Section A', 'A'
                    FROM admission_cohorts WHERE code = 'LAT'$$,
                'another batch can reuse the section code A');
SELECT throws_ok($$INSERT INTO academic_sections (institution_id, admission_cohort_id, program_semester_id, semester_id, name, code)
                   VALUES ('00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-00000000000b',
                           '00000000-0000-4000-8000-000000000008', '00000000-0000-4000-8000-000000000006', 'Section A again', ' a ')$$,
                 '23505', NULL, 'the same batch semester cannot reuse a section code, ignoring case and spaces');
SELECT lives_ok($$INSERT INTO academic_sections (institution_id, admission_cohort_id, program_semester_id, semester_id, name, code)
                  VALUES ('00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-00000000000b',
                          '00000000-0000-4000-8000-000000000018', '00000000-0000-4000-8000-000000000006', 'Section A', 'A')$$,
                'Section A can continue into the batch''s next program semester');

-- Tenant isolation
SELECT throws_ok($$INSERT INTO academic_sections (institution_id, admission_cohort_id, program_semester_id, semester_id, name, code)
                   VALUES ('00000000-0000-4000-8000-0000000000f2', '00000000-0000-4000-8000-00000000000b',
                           '00000000-0000-4000-8000-000000000008', '00000000-0000-4000-8000-000000000006', 'Foreign', 'FX')$$,
                 NULL, NULL, 'a section cannot use another institution''s batch');
SELECT lives_ok($$INSERT INTO departments (institution_id, name, code)
                  VALUES ('00000000-0000-4000-8000-0000000000f2', 'CSE', 'CSE')$$,
                'another institution can reuse the same department code');
SELECT throws_ok($$INSERT INTO departments (institution_id, name, code)
                   VALUES ('00000000-0000-4000-8000-000000000002', 'Duplicate', 'cse')$$,
                 '23505', NULL, 'department codes are unique per institution, ignoring case');

SELECT * FROM finish();
ROLLBACK;
