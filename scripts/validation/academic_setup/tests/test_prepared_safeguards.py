"""Prepared SQL contract checks only; these do not establish PostgreSQL behavior."""
import re
from unittest.mock import Mock

from scripts.validation.academic_setup.concurrency import run_concurrency
from scripts.validation.academic_setup.inputs import load_plan
from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.tests.support import OfflineCase
from scripts.validation.academic_setup.tests.test_workflow import RecordingSession
from scripts.validation.academic_setup.workflow import execute_plan, snapshot_sql


class PreparedSafeguardTests(OfflineCase):
    def test_approved_inventory_matches_actual_academic_migration_contracts(self):
        plan = load_plan()
        snapshot = snapshot_sql(plan)
        definitions = '\n'.join(item.text for item in plan.migrations[46:])
        expected_tables = set(re.findall(r'CREATE TABLE public\.([a-z_]+)', definitions))
        expected_routines = set()
        for name, arguments in re.findall(
                r'CREATE FUNCTION public\.([a-z_]+)\((.*?)\)\s*RETURNS', definitions, re.DOTALL):
            types = [argument.split()[-1] for argument in arguments.split(',') if argument.strip()]
            expected_routines.add('public.' + name + '(' + ','.join(types) + ')')
        tables = re.search(r"'tables',ARRAY\[(.*?)\]", snapshot, re.DOTALL).group(1)
        routines = re.search(r"'routines',ARRAY\[(.*?)\]", snapshot, re.DOTALL).group(1)
        self.assertEqual(set(re.findall(r"'public\.([a-z_]+)'", tables)), expected_tables)
        self.assertEqual(set(re.findall(r"'(public\.[^']+)'", routines)), expected_routines)
        self.assertEqual(len(expected_tables), 7)
        self.assertEqual(len(expected_routines), 9)
        self.assertIn("'sequences','[]'::jsonb", snapshot)
        self.assertNotRegex(definitions, r'CREATE SEQUENCE')

    def test_full_inventory_and_retained_state_are_both_verified(self):
        snapshot = snapshot_sql(load_plan())
        self.assertIn("('post_decommission_catalog','{}')", snapshot)
        self.assertIn("assert_catalog_inventory(inventory->'inventory',catalog_state->'inventory')", snapshot)
        self.assertIn("c.relkind IN ('r','p','v','m','f')", snapshot)
        self.assertIn('jsonb_object_keys(previous->group_name)', snapshot)
        self.assertIn('jsonb_object_keys(current_state->group_name)', snapshot)
        self.assertIn("ERRCODE='P4201'", snapshot)
        self.assertIn("ERRCODE='P4202'", snapshot)
        self.assertIn('current_group->item.key IS DISTINCT FROM item.value', snapshot)
        self.assertIn("THEN previous ELSE inventory END", snapshot)
        self.assertIn("THEN current_state ELSE catalog_state END", snapshot)

    def test_unexpected_objects_and_retained_changes_have_rollback_negative_controls(self):
        text = load_plan().sql('probes/object_inventory')
        for command in ('CREATE TABLE public.academic_unexpected_probe',
                        'CREATE FUNCTION public.academic_unexpected_probe',
                        'CREATE PROCEDURE public.academic_unexpected_probe', 'PARTITION BY RANGE(id)',
                        'CREATE SEQUENCE public.academic_unexpected_probe',
                        'ADD COLUMN note text', 'DROP TABLE public.academic_retained_inventory_probe',
                        'CREATE OR REPLACE FUNCTION public.academic_retained_inventory_probe',
                        'DROP FUNCTION public.academic_retained_inventory_probe()',
                        'ALTER SEQUENCE public.academic_retained_inventory_sequence',
                        'DROP SEQUENCE public.academic_retained_inventory_sequence',
                        'assert_catalog_inventory(NULL,NULL)'):
            self.assertIn(command, text)
        self.assertIn("'P4201'", text)
        self.assertIn("'P4202'", text)
        self.assertIn('expect_error(', text)
        self.assertIn('IS DISTINCT FROM baseline', text)
        self.assertTrue(text.rstrip().endswith('ROLLBACK;'))

    def test_trigger_rls_and_sequence_mutations_use_the_restoring_probe(self):
        text = load_plan().sql('probes/snapshot_differences')
        self.assertLess(text.index('CREATE TRIGGER existing_probe'), text.index('DISABLE TRIGGER existing_probe'))
        self.assertIn('CREATE SEQUENCE public.academic_snapshot_sequence', text)
        self.assertIn('SELECT academic_setup_check.expect_snapshot_change(command)', text)
        self.assertIn('FORCE ROW LEVEL SECURITY', text)
        self.assertIn('INCREMENT BY 7', text)
        self.assertIn('OWNER TO academic_snapshot_owner', text)
        self.assertIn('GRANT USAGE ON SEQUENCE', text)
        self.assertIn("EXCEPTION WHEN SQLSTATE 'P4099' THEN NULL", text)
        self.assertIn('Snapshot mutation did not roll back', text)

    def test_role_probes_switch_database_role_and_require_exact_permission_denial(self):
        text = load_plan().sql('probes/privilege_roles')
        helper = text.split('DO $$', 1)[0]
        self.assertIn('SECURITY INVOKER', helper)
        self.assertNotIn('SECURITY DEFINER', helper)
        self.assertIn("SET LOCAL ROLE %I", helper)
        self.assertIn('current_user<>role_name', helper)
        self.assertIn('RESET ROLE;', helper)
        self.assertIn('actual_state IS DISTINCT FROM expected_state', helper)
        self.assertNotIn('PERFORM academic_setup_check.', helper)
        self.assertIn("ARRAY['anon','authenticated','service_role']", text)
        for command in ('INSERT INTO public.%I', 'UPDATE public.%I', 'DELETE FROM public.%I',
                        'TRUNCATE TABLE public.%I', 'SELECT public.assert_academic_foundation_actor',
                        'SELECT public.guard_academic_sections_parent()'):
            self.assertIn(command, text)
        self.assertIn("as_role(browser,command,'42501')", text)
        self.assertIn("as_role('service_role',command)", text)
        for routine in ('manage_academic_foundation', 'manage_academic_structure', 'manage_academic_sections'):
            self.assertIn(routine, text)
        self.assertIn('Denied database-role requests changed state', text)
        self.assertIn('record_data->\'after\'=response', text)
        self.assertTrue(text.rstrip().endswith('ROLLBACK;'))

    def test_new_probe_failures_stop_replay_and_run_owned_cleanup(self):
        plan = load_plan()
        recorded = RecordingSession()
        execute_plan(recorded, plan)
        for name in ('probes/object_inventory', 'probes/catalog_retention', 'probes/privilege_roles'):
            text = plan.sql(name)
            position = next(i for i, (sql, _) in enumerate(recorded.statements) if sql == text)
            failing = RecordingSession(fail_at=position+1)
            with self.subTest(probe=name), self.assertRaises(HarnessError):
                execute_plan(failing, plan)
            self.assertEqual(failing.actions[-1], 'cleanup')
            self.assertNotIn(plan.sql('concurrency/setup'), [sql for sql, _ in failing.statements])

    def test_concurrency_audits_compare_exact_row_identity_and_transitions(self):
        plan = load_plan()
        text = plan.sql('concurrency/verify')
        self.assertIn("'race_parent_before',r", plan.sql('concurrency/setup'))
        for clause in ("record_id=created->>'department_id'", "record_id=a->>'race_parent'",
                       "actor_user_id=(b->>'actor')::uuid", "actor_user_id=(a->>'actor')::uuid",
                       "action='academic.departments.create'", "action='academic.departments.deactivate'",
                       "record_data->'before'='null'::jsonb", "record_data->'after'=created",
                       "record_data->'before'=a->'race_parent_before'", "record_data->'after'=parent_after",
                       "code='RACE_CHILD'", "record_data->'after'->>'code'='RACE_CHILD'"):
            self.assertIn(clause, text)
        self.assertIn("record_id=created->>'department_id')<>1", text)
        self.assertIn("record_id=a->>'race_parent')<>2", text)

    def test_failed_audit_verification_prevents_synthetic_teardown(self):
        plan = load_plan()
        calls = []

        def sql(text):
            calls.append(text)
            if text == plan.sql('concurrency/verify'):
                raise HarnessError('Audit evidence differs')

        with self.assertRaisesRegex(HarnessError, 'Audit evidence'):
            run_concurrency(Mock(sql=sql), plan)
        self.assertNotIn(plan.sql('concurrency/teardown'), calls)
        self.assertEqual(calls[-1], plan.sql('concurrency/verify'))
