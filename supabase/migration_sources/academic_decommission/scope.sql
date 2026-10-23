-- Explicitly authorized removal of Academic Setup and its dependent academic
-- modules. Account identity, approval, tenancy and nonacademic data survive.
SET LOCAL lock_timeout = '10s';
CREATE TEMP TABLE academic_decommission_tables(name text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO academic_decommission_tables(name) VALUES
    ('academic_curricula'), ('academic_curriculum_subjects'), ('academic_subject_packages'),
    ('academic_package_subjects'), ('academic_classes'), ('academic_class_packages'),
    ('academic_class_subjects'), ('academic_class_responsibilities'), ('academic_class_placements'),
    ('academic_package_assignments'), ('academic_package_revisions'), ('academic_subject_participation'),
    ('academic_package_requests'), ('academic_years'), ('semesters'), ('departments'), ('programs'),
    ('courses'), ('program_courses'), ('course_offerings'), ('sections'), ('academic_batches'),
    ('student_registrations'), ('student_registration_invitations'), ('student_results'),
    ('student_result_items'), ('test_results'), ('student_attendance'), ('faculty_attendance_rosters'),
    ('faculty_attendance_sessions'), ('faculty_attendance_records'), ('faculty_attendance_imports'),
    ('faculty_attendance_import_rows'), ('faculty_section_assignments'), ('responsibility_definitions'),
    ('responsibility_permissions'), ('faculty_responsibilities'), ('faculty_tests'), ('test_types');

CREATE TEMP TABLE academic_decommission_functions(name text PRIMARY KEY) ON COMMIT DROP;
INSERT INTO academic_decommission_functions(name) VALUES
    ('academic_package_actor'), ('academic_package_allowed'), ('academic_package_require'),
    ('academic_package_owns'), ('academic_package_audit'), ('academic_package_editable'),
    ('academic_package_curriculum_command'), ('academic_package_class_command'), ('academic_package_place'),
    ('academic_package_roster_active'), ('academic_package_subject_roster'), ('academic_package_apply'),
    ('academic_package_request_command'), ('academic_package_catalogue'), ('academic_legacy_section_authorize'),
    ('assign_student_subject'), ('delete_academic_roster'), ('academic_package_roster_guard'),
    ('academic_package_participates_on'), ('academic_package_event_guard'), ('academic_package_no_truncate'),
    ('academic_package_roster_has_placement'), ('academic_package_roster_context'),
    ('academic_package_identity_for_roster'), ('academic_package_offering_eligibility'),
    ('academic_package_prepare_teaching'), ('academic_package_command'),
    ('student_attendance_tenant_guard'), ('test_results_tenant_guard'), ('student_results_tenant_guard'),
    ('faculty_attendance_set_updated_at'), ('faculty_attendance_context_guard'),
    ('faculty_attendance_record_scope_guard'), ('reconcile_faculty_attendance_roster_student'),
    ('faculty_responsibility_scope_guard'), ('faculty_assignment_touch'), ('manage_faculty_responsibility'),
    ('update_faculty_teaching_validity'), ('phase81_manage_faculty_section_assignment'),
    ('phase81_manage_faculty_section_assignment_original'),
    ('create_faculty_teaching_assignment'), ('manage_scoped_faculty_teaching_assignment'),
    ('assert_faculty_attendance_mutation'), ('faculty_attendance_identity'), ('mark_faculty_attendance'),
    ('review_faculty_attendance_import'), ('stage_faculty_attendance_import'), ('commit_faculty_attendance_import'),
    ('assert_faculty_academic_mutation'), ('faculty_test_context_guard'), ('guard_workflow_result_delete'),
    ('assert_test_version'), ('validate_test_schedule'), ('save_faculty_test'), ('save_faculty_test_marks'),
    ('transition_faculty_test'), ('stage_faculty_test_import'), ('review_faculty_test_import'),
    ('commit_faculty_test_import'), ('reconcile_faculty_test_roster'), ('refresh_student_test_visibility'),
    ('guard_test_import_workflow'), ('academic_master_tenant'), ('validate_academic_master_record'),
    ('manage_academic_master_record'), ('guard_student_registration_scope'), ('guard_academic_batch'),
    ('guard_student_registration_batch'), ('manage_academic_batch'), ('claim_student_registration_invitation'),
    ('complete_student_registration_invitation');

CREATE TEMP TABLE academic_decommission_permissions(permission_id uuid PRIMARY KEY) ON COMMIT DROP;
INSERT INTO academic_decommission_permissions SELECT permission_id FROM public.permissions
WHERE code ~ '^(academic\.|attendance\.|results\.|faculty\.assignments\.|departments\.|courses\.|subjects\.|semesters\.|academic_years\.)';

CREATE TEMP TABLE academic_decommission_preserved(
    schema_name text, table_name text, rows jsonb, PRIMARY KEY(schema_name, table_name)
) ON COMMIT DROP;
CREATE TEMP TABLE academic_decommission_routines(oid oid PRIMARY KEY, definition text) ON COMMIT DROP;
