"""Prepared SQL controls and ordering; these never execute SQL."""
import re

from scripts.validation.academic_setup.inputs import load_plan
from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.tests.support import OfflineCase
from scripts.validation.academic_setup.tests.test_workflow import RecordingSession
from scripts.validation.academic_setup.workflow import execute_plan, late_failure, snapshot_sql


class RetainedStateTests(OfflineCase):
    def test_every_category_is_captured_before_first_decommission_submission(self):
        plan = load_plan()
        session = RecordingSession()
        execute_plan(session, plan)
        snapshot = snapshot_sql(plan)
        texts = [text for text, _ in session.statements]
        first_decommission = next(i for i, (text, _) in enumerate(session.statements)
                                  if text == plan.migrations[45].text)
        self.assertLess(texts.index(snapshot), first_decommission)
        self.assertLess(snapshot.index(plan.sql('snapshots/fixtures')),
                        snapshot.index("('retained',academic_setup_check.capture(false))"))
        self.assertIn('ELSE academic_setup_check.retained_inventory() END', snapshot)
        for kind in ('view', 'materialized', 'partition', 'foreign', 'procedure', 'aggregate', 'window'):
            self.assertIn('public.academic_preserved_'+kind, plan.sql('snapshots/fixtures'))
        self.assertIn('verify_decommission_retained()', plan.sql('retained_verify'))

    def test_original_comparison_cannot_read_later_snapshots_as_its_baseline(self):
        text = load_plan().sql('snapshots/retained')
        body = text.split('CREATE FUNCTION academic_setup_check.verify_decommission_retained()', 1)[1]
        body = body.split('END $$;', 1)[0]
        self.assertIn("WHERE name='retained'", body)
        self.assertNotIn('post_decommission', body)
        self.assertIn('assert_retained_state(original,academic_setup_check.capture(false))', body)
        comparator = text.split('assert_retained_state(original jsonb, current_state jsonb)', 1)[1].split('END $$;', 1)[0]
        self.assertIn('current_state IS DISTINCT FROM original', comparator)
        self.assertIn("ERRCODE='P4202'", comparator)
        for group in ('tables', 'routines', 'sequences'):
            self.assertIn("'inventory'->'"+group+"'", comparator)

    def test_original_projection_ignores_only_sanctioned_body_fields(self):
        text = load_plan().sql('snapshots/retained')
        self.assertIn('public.phase81_manage_staff_permission_grants(uuid,uuid,uuid,text[],boolean)', text)
        self.assertIn("ARRAY['routines',item.signature,'definition']", text)
        self.assertIn("ARRAY['routines',item.signature,'catalog','prosrc']", text)
        self.assertNotIn("item.proname='phase81_manage_staff_permission_grants'", text)
        self.assertIn("v->>'name' NOT IN ('program_id','academic_year_id')", text)

    def test_mutation_controls_run_inside_decommission_before_commit_and_roll_back(self):
        plan = load_plan()
        controls = plan.sql('probes/decommission_retention') + plan.sql('probes/catalog_properties')
        variant = late_failure(plan.migrations[45].text, control=controls)
        session = RecordingSession()
        execute_plan(session, plan)
        position = session.statements.index((variant, 'P4001'))
        self.assertEqual(session.statements[position+1], (plan.sql('rollback_verify'), None))
        self.assertNotIn(controls, plan.migrations[45].text)
        self.assertLess(variant.index(controls), variant.rindex('COMMIT;'))
        for newline in ('\n', '\r\n'):
            original = newline.join(['BEGIN;', 'SELECT 1;', 'COMMIT;', ''])
            injected = controls + "DO $$ BEGIN RAISE EXCEPTION USING ERRCODE='P4001'; END $$;" + newline
            self.assertEqual(late_failure(original, control=controls).replace(injected, ''), original)

    def test_failed_decommission_control_stops_before_permanent_replay(self):
        plan = load_plan()
        recorded = RecordingSession()
        execute_plan(recorded, plan)
        position = next(i for i, (text, _) in enumerate(recorded.statements)
                        if plan.sql('probes/decommission_retention') in text)
        failing = RecordingSession(fail_at=position+1)
        with self.assertRaises(HarnessError):
            execute_plan(failing, plan)
        self.assertEqual(failing.actions[-1], 'cleanup')
        self.assertNotIn((plan.migrations[45].text, None), failing.statements)
        self.assertNotIn((plan.sql('concurrency/setup'), None), failing.statements)

    def test_same_name_controls_test_original_baseline_even_after_later_rebase(self):
        plan = load_plan()
        controls = plan.sql('probes/decommission_retention')
        helper = plan.sql('snapshots/retained').split('expect_retained_change(command text)', 1)[1]
        self.assertLess(helper.index('UPDATE academic_setup_check.snapshots'),
                        helper.index('PERFORM academic_setup_check.verify_decommission_retained()'))
        self.assertIn("WHERE name IN ('post_decommission','post_decommission_catalog')", helper)
        self.assertIn("EXCEPTION WHEN SQLSTATE 'P4202'", helper)
        self.assertIn("EXCEPTION WHEN SQLSTATE 'P4099'", helper)
        self.assertIn('IS DISTINCT FROM baseline', helper)
        for name in ('view', 'materialized', 'partition', 'foreign', 'procedure', 'aggregate', 'window'):
            self.assertRegex(controls, 'academic_preserved_'+name+r'[^\n]*OWNER TO')
            self.assertRegex(controls, r'GRANT [^\n]*academic_preserved_'+name)

    def test_reported_catalog_properties_have_capture_fields_and_controls(self):
        plan = load_plan()
        capture = plan.sql('snapshots/catalog')
        controls = plan.sql('probes/catalog_properties')
        for field, control in (
            ('r.ev_enabled', 'CREATE RULE'), ('c.relreplident', 'REPLICA IDENTITY FULL'),
            ('i.indisclustered', 'CLUSTER ON'), ('a.attfdwoptions', 'ALTER COLUMN id OPTIONS'),
            ('s.srvtype', "TYPE ''other''"), ('s.srvversion', "VERSION ''two''"),
            ('d.refobjsubid', 'OWNED BY public.academic_preserved_table.id'),
            ('c.relpersistence', 'SET UNLOGGED'),
        ):
            with self.subTest(field=field):
                self.assertIn(field, capture)
                self.assertIn(control, controls)
        rules = capture.split("'rules',", 1)[1].split('FROM pg_class', 1)[0]
        self.assertNotIn("c.relkind<>'r'", rules)
        self.assertIn('pg_get_ruledef', rules)

    def test_index_flags_are_captured_without_direct_system_catalog_mutation(self):
        plan = load_plan()
        for text in (plan.sql('snapshot'), plan.sql('snapshots/catalog')):
            for field in ('indisvalid', 'indisready', 'indisclustered'):
                self.assertIn(field, text)
        controls = plan.sql('probes/catalog_properties')
        self.assertIn("ARRAY['valid','ready','clustered']", controls)
        self.assertIn("'public.academic_preserved_materialized','public.academic_preserved_partition'", controls)
        self.assertIn('assert_catalog_inventory(original,changed)', controls)
        self.assertIn('assert_retained_state(original,changed)', controls)
        self.assertEqual(controls.count("IS DISTINCT FROM 'boolean'"), 2)
        self.assertIn("IF SQLERRM<>'Retained pre-decommission state changed' THEN RAISE", controls)
        self.assertIn("IF SQLERRM<>'Retained object changed during Academic Setup replay' THEN RAISE", controls)
        self.assertNotRegex(controls, r'(?i)(UPDATE|INSERT INTO|DELETE FROM)\s+pg_(index|class)')

    def test_finalization_never_deletes_audits_or_bypasses_pinned_trigger(self):
        plan = load_plan()
        pinned = plan.migrations[27].text
        self.assertIn('phase81_admin_audit_append_only', pinned)
        self.assertIn('BEFORE UPDATE OR DELETE', pinned)
        self.assertIn("RAISE EXCEPTION 'Audit records are append-only'", pinned)
        sql = '\n'.join(plan.sql('concurrency/'+name) for name in ('setup', 'verify', 'teardown'))
        self.assertNotRegex(sql, r'(?i)\b(DELETE|TRUNCATE|DISABLE\s+TRIGGER|session_replication_role)\b')
        self.assertIn('verify_post_academic()', plan.sql('concurrency/teardown'))
        self.assertIn("relation_name='public.admin_audit_log')<>20", plan.sql('concurrency/teardown'))

    def test_fixture_projection_requires_exact_registered_rows(self):
        plan = load_plan()
        setup = plan.sql('concurrency/setup')
        self.assertIn('PRIMARY KEY(relation_name,row_data)', setup)
        self.assertIn('WHERE v=item.row_data)<>1', setup)
        self.assertIn('r.row_data=v', setup)
        self.assertNotIn("v->>'institution_id'", setup)
        self.assertIn('Recorded committed fixture row changed or disappeared', setup)
        verify = plan.sql('concurrency/verify')
        self.assertLess(verify.index('Tenant A race audit identity or transition differs'),
                        verify.index('INSERT INTO academic_setup_check.race_expected_rows'))
        self.assertIn('Tenant B creation audit count, identity or transition differs', verify)
        self.assertIn('Parent deactivation audit count, identity or transition differs', verify)
