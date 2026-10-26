from scripts.validation.academic_setup.check_structure import check_structure
from scripts.validation.academic_setup.inputs import load_plan
from scripts.validation.academic_setup.tests.support import OfflineCase
from scripts.validation.academic_setup.tests.test_workflow import RecordingSession
from scripts.validation.academic_setup.workflow import execute_plan, snapshot_sql


class SqlContractTests(OfflineCase):
    """Static wiring checks; SQL assertions require a separately approved live run."""

    def test_catalog_dimensions_have_executable_mutation_difference_probes(self):
        plan = load_plan()
        capture = snapshot_sql(plan)
        changes = plan.sql('probes/snapshot_differences')
        for catalog, alteration in (
            ('pg_get_triggerdef', 'CREATE TRIGGER'), ('pg_policy', 'CREATE POLICY'),
            ('pg_get_indexdef', 'CREATE INDEX'), ('relowner', 'ALTER TABLE'),
            ('attacl', 'GRANT UPDATE(note)'), ('proowner', 'ALTER FUNCTION'),
            ('proacl', 'REVOKE EXECUTE'), ('nspacl', 'GRANT CREATE ON SCHEMA'),
            ('pg_default_acl', 'ALTER DEFAULT PRIVILEGES'), ('relacl', 'GRANT SELECT'),
            ('tgenabled', 'DISABLE TRIGGER existing_probe'),
            ('relforcerowsecurity', 'FORCE ROW LEVEL SECURITY'),
            ('seqincrement', 'ALTER SEQUENCE public.academic_snapshot_sequence INCREMENT BY 7'),
            ('relowner', 'ALTER SEQUENCE public.academic_snapshot_sequence OWNER TO'),
            ('relacl', 'GRANT USAGE ON SEQUENCE public.academic_snapshot_sequence')):
            with self.subTest(catalog=catalog):
                self.assertIn(catalog, capture)
                self.assertIn(alteration, changes)
        self.assertIn('IS NOT DISTINCT FROM before_state', changes)
        self.assertIn("ERRCODE='P4099'", changes)
        self.assertIn('relforcerowsecurity', capture)

    def test_real_prerequisite_rejection_and_late_rollback_are_distinct_lanes(self):
        plan = load_plan()
        session = RecordingSession()
        execute_plan(session, plan)
        calls = session.statements
        rejected = next(i for i, (_, state) in enumerate(calls) if state == 'P0001')
        late = next(i for i, (_, state) in enumerate(calls) if state == 'P4001')
        self.assertEqual(calls[rejected][0], plan.migrations[45].text)
        self.assertEqual(calls[rejected-1][0], plan.sql('prerequisite_violation'))
        self.assertEqual(calls[rejected+1][0], plan.sql('rollback_verify'))
        self.assertEqual(calls[rejected+2][0], plan.sql('prerequisite_restore'))
        self.assertLess(rejected, late)
        self.assertIn('REFERENCES public.programs(program_id)', plan.sql('prerequisite_violation'))
        self.assertIn('Unexpected preserved-table foreign key into academic domain; removal refused',
                      plan.migrations[45].text)

    def test_expanded_sql_is_pinned_wired_and_rollback_only_for_single_sessions(self):
        plan = load_plan()
        session = RecordingSession()
        execute_plan(session, plan)
        texts = [text for text, _ in session.statements]
        for name in ('tenancy_authority', 'lifecycle', 'audit_atomicity'):
            text = plan.sql('probes/' + name)
            self.assertIn(text, texts)
            self.assertTrue(text.startswith('BEGIN;'))
            self.assertTrue(text.rstrip().endswith('ROLLBACK;'))
        for clause in ('delegated_only', 'admin_delegated_only', 'split_role_provenance', 'foreign_admin_local_staff',
                       'inactive_user', 'inactive_role', 'inactive_permission', 'organization_authority'):
            self.assertIn(clause, plan.sql('probes/tenancy_authority'))
        self.assertIn("'23514',NULL,'academic_probe_deny'", plan.sql('probes/audit_atomicity'))

    def test_security_covers_column_privileges_helpers_and_function_configuration(self):
        text = load_plan().sql('security_probes')
        for clause in ('has_any_column_privilege', 'REFERENCES,TRIGGER', 'MAINTAIN',
                       'prosecdef', 'proconfig', 'proowner', 'relowner',
                       'assert_academic_foundation_actor', 'guard_academic_sections_parent'):
            self.assertIn(clause, text)

    def test_harness_stays_within_folder_and_file_limits(self):
        self.assertEqual(check_structure(), [])
