"""Source contracts and prepared controls; no PostgreSQL syntax/runtime proof."""
import re

from scripts.validation.academic_setup.inputs import load_plan
from scripts.validation.academic_setup.tests.support import OfflineCase
from scripts.validation.academic_setup.workflow import snapshot_sql


class SourceReviewTests(OfflineCase):
    def contracts(self):
        plan = load_plan()
        definitions = '\n'.join(item.text for item in plan.migrations[46:])
        found = {}
        for name, arguments, result in re.findall(
                r'CREATE FUNCTION public\.([a-z_]+)\((.*?)\)\s*RETURNS (\w+)', definitions, re.DOTALL):
            types = [arg.split()[-1] for arg in arguments.split(',') if arg.strip()]
            found['public.'+name+'('+','.join(types)+')'] = result
        return plan, definitions, found

    def test_every_role_probe_signature_and_return_type_matches_pinned_migrations(self):
        plan, _, contracts = self.contracts()
        text = plan.sql('probes/privilege_roles')
        rows = re.findall(r"\('(public\.[^']+)','(void|trigger|jsonb)',(true|false)\)", text)
        self.assertEqual({signature: result for signature, result, _ in rows}, contracts)
        self.assertEqual(len(rows), 9)
        for signature, result, rpc in rows:
            self.assertEqual(rpc == 'true', result == 'jsonb', signature)
        self.assertIn('p.prorettype=to_regtype(item.result_type)', text)
        self.assertIn("p.prokind='f'", text)
        self.assertIn('NOT p.proretset', text)

    def test_all_six_private_calls_and_three_rpc_grants_match_exact_pins(self):
        plan, definitions, contracts = self.contracts()
        normalize = lambda text: re.sub(r'\s+', '', text)
        granted = set(normalize(signature) for signature in re.findall(
            r'GRANT EXECUTE ON FUNCTION (public\.[^;]+?) TO service_role;', definitions))
        expected = {signature for signature, result in contracts.items() if result == 'jsonb'}
        self.assertEqual(granted, expected)
        revoked = set()
        for clause in re.findall(r'REVOKE ALL ON FUNCTION (.*?)FROM PUBLIC, anon, authenticated, service_role;',
                                 definitions, re.DOTALL):
            revoked.update(normalize(signature) for signature in re.findall(r'public\.[a-z_]+\([^)]*\)', clause))
        self.assertEqual(revoked, set(contracts))
        text = plan.sql('probes/privilege_roles')
        actual_helpers = set(re.findall(r'SELECT public\.([a-z_]+)\(', text))
        expected_helpers = {signature.split('.')[1].split('(')[0]
                            for signature, result in contracts.items() if result != 'jsonb'}
        self.assertEqual(actual_helpers, expected_helpers)
        self.assertIn("(item.rpc AND browser='service_role')", text)
        self.assertIn("as_role(browser,command,'42501')", text)

    def test_denial_lane_does_not_coerce_void_or_trigger_results_to_jsonb(self):
        text = load_plan().sql('probes/privilege_roles')
        branches = re.search(r'IF expected_state IS NULL THEN(.*?)ELSE(.*?)END IF;', text, re.DOTALL)
        self.assertIn('EXECUTE command INTO STRICT response;', branches.group(1))
        self.assertIn('EXECUTE command;', branches.group(2))
        self.assertNotIn('INTO response', branches.group(2))
        self.assertIn('actual_state IS DISTINCT FROM expected_state', text)

    def test_rpc_controls_match_return_rows_actions_and_audit_relation_names(self):
        plan, definitions, _ = self.contracts()
        self.assertEqual(definitions.count('RETURN after_row;'), 3)
        normalized = re.sub(r'\s+', '', definitions)
        self.assertEqual(normalized.count("jsonb_build_object('before',before_row,'after',after_row)"), 3)
        text = plan.sql('probes/privilege_roles')
        for row in ("'departments','department_id','departments'",
                    "'subjects','subject_id','subjects'", "'sections','section_id','class_sections'"):
            self.assertEqual(text.count(row), 2)
        for clause in ("action='academic.'||item.entity||'.create'", 'table_name=item.relation_name',
                       'record_id=response->>item.key', "record_data->'before'='null'::jsonb",
                       "record_data->'after'=response", "jsonb_typeof(response) IS DISTINCT FROM 'object'"):
            self.assertIn(clause, text)

    def test_inventory_compares_existing_metadata_not_just_keys(self):
        snapshot = snapshot_sql(load_plan())
        self.assertIn('current_state->group_name->object_name IS DISTINCT FROM previous->group_name->object_name', snapshot)
        for clause in ('pg_get_viewdef', 'pg_get_partkeydef', 'pg_foreign_table', 'pg_get_ruledef',
                       'pg_aggregate', 'to_jsonb(p)', "p.prokind<>'a'", 'p.proowner', 'p.proacl',
                       'c.relowner', 'c.relacl', 'a.attacl'):
            self.assertIn(clause, snapshot)
        self.assertNotIn("p.prokind='f'", load_plan().sql('snapshots/catalog'))
        self.assertNotIn('SELECT * FROM public.', load_plan().sql('snapshots/catalog'))

    def test_same_name_controls_cover_definition_owner_and_acl_for_all_added_types(self):
        text = load_plan().sql('probes/catalog_retention')
        for name in ('view', 'materialized', 'partition', 'foreign', 'procedure', 'aggregate', 'window'):
            with self.subTest(kind=name):
                self.assertIn('academic_retained_'+name, text)
                self.assertRegex(text, r'[^\n]*academic_retained_'+name+r'[^\n]*OWNER TO academic_retention_owner')
                self.assertRegex(text, r'GRANT [^\n]*academic_retained_'+name+r'[^\n]*TO anon')
        for clause in ('CREATE OR REPLACE VIEW', 'DROP MATERIALIZED VIEW', 'PARTITION BY LIST(id)',
                       "OPTIONS (SET probe ''two'')", 'CREATE OR REPLACE PROCEDURE', 'SFUNC=pg_catalog.int8mi',
                       "WINDOW AS ''window_rank''", "'P4202'", "ERRCODE='P4099'", 'IS DISTINCT FROM baseline'):
            self.assertIn(clause, text)
        self.assertIn('NO HANDLER NO VALIDATOR', text)
        self.assertTrue(text.rstrip().endswith('ROLLBACK;'))

    def test_ownership_acl_probe_preconditions_are_explicit_and_transactional(self):
        text = load_plan().sql('probes/snapshot_differences')
        for clause in ('GRANT USAGE,CREATE ON SCHEMA public TO academic_snapshot_owner',
                       "has_schema_privilege('academic_snapshot_owner','public','CREATE')",
                       "pg_has_role(current_user,'academic_snapshot_owner','SET')", 'aclexplode',
                       "acl.grantee=0 AND acl.privilege_type='EXECUTE'", "deptype IN ('a','i')",
                       'Snapshot ownership or ACL mutation preconditions differ'):
            self.assertIn(clause, text)
        self.assertLess(text.index('REVOKE ALL ON SEQUENCE'), text.index('before_state :='))
        self.assertLess(text.index('mutation preconditions differ'), text.index('before_state :='))
        self.assertIn('Snapshot mutation did not roll back', text)
        self.assertTrue(text.rstrip().endswith('ROLLBACK;'))
