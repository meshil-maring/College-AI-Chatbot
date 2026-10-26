from contextlib import redirect_stdout
from io import StringIO
import json
import sys
from unittest.mock import patch

from scripts.validation.academic_setup.__main__ import main
from scripts.validation.academic_setup.inputs import LEGACY_FIXTURE, load_plan
from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.workflow import execute_plan, late_failure, replay, snapshot_sql
from scripts.validation.academic_setup.tests.support import OfflineCase


class RecordingSession:
    def __init__(self, fail_at=None, cleanup_failure=False):
        self.statements = []
        self.actions = []
        self.fail_at = fail_at
        self.cleanup_failure = cleanup_failure

    def create(self):
        self.actions.append("create")

    def start(self):
        self.actions.append("start")

    def ready(self):
        self.actions.append("ready")

    def sql(self, text, *, expected_sqlstate=None, expected_message=None):
        self.statements.append((text, expected_sqlstate))
        if len(self.statements) == self.fail_at:
            raise HarnessError("Injected verification failure")

    def cleanup(self):
        self.actions.append("cleanup")
        if self.cleanup_failure:
            raise HarnessError("Injected cleanup failure")


class WorkflowTests(OfflineCase):
    def test_replay_preserves_each_original_file_and_stops_at_first_failure(self):
        plan = load_plan()
        session = RecordingSession(fail_at=3)
        with self.assertRaises(HarnessError):
            replay(session, plan.migrations[:45])
        self.assertEqual(session.statements,
                         [(item.text, None) for item in plan.migrations[:3]])

    def test_future_workflow_orders_baseline_fixture_rollback_retention_and_four_releases(self):
        plan = load_plan()
        session = RecordingSession()
        execute_plan(session, plan)
        statements = [text for text, _ in session.statements]
        self.assertEqual(session.actions, ["create", "start", "ready", "cleanup"])
        self.assertEqual(statements[2:47], [item.text for item in plan.migrations[:45]])
        self.assertEqual(statements[47], plan.inputs[LEGACY_FIXTURE].text)
        negative = next(index for index, (_, state) in enumerate(session.statements) if state == "P4001")
        decommission = next(index for index, (text, state) in enumerate(session.statements)
                            if text == plan.migrations[45].text and state is None)
        self.assertLess(negative, decommission)
        retained = statements.index(plan.sql("retained_verify"))
        self.assertGreater(retained, decommission)
        self.assertLess(retained, statements.index(plan.migrations[46].text))
        for before, after in zip(plan.migrations[45:], plan.migrations[46:]):
            self.assertLess(statements.index(before.text), statements.index(after.text))
        self.assertGreater(statements.index(plan.sql("academic_probes")),
                           statements.index(plan.migrations[-1].text))

    def test_failure_runs_cleanup_and_does_not_run_later_phases(self):
        session = RecordingSession(fail_at=5)
        with self.assertRaisesRegex(HarnessError, "Injected verification"):
            execute_plan(session, load_plan())
        self.assertEqual(len(session.statements), 5)
        self.assertEqual(session.actions[-1], "cleanup")

    def test_cleanup_failure_is_explicit_and_never_claims_success(self):
        session = RecordingSession(fail_at=1, cleanup_failure=True)
        with self.assertRaisesRegex(HarnessError, "cleanup unverified"):
            execute_plan(session, load_plan())

    def test_late_rollback_variant_keeps_one_outer_transaction_and_original_immutable(self):
        original = load_plan().migrations[45].text
        variant = late_failure(original)
        normalized = variant.replace("\r\n", "\n")
        self.assertEqual(normalized.count("\nBEGIN;\n"), 1)
        self.assertEqual(normalized.count("\nCOMMIT;\n"), 1)
        self.assertIn("ERRCODE='P4001'", variant)
        self.assertNotIn("ERRCODE='P4001'", original)
        with self.assertRaises(HarnessError):
            late_failure("SELECT 1;")

    def test_rollback_variant_preserves_lf_and_crlf_bytes_outside_injected_probe(self):
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                original = newline.join(["BEGIN;", "SELECT 1;", "COMMIT;", ""])
                variant = late_failure(original)
                injected = "DO $$ BEGIN RAISE EXCEPTION USING ERRCODE='P4001'; END $$;" + newline
                self.assertEqual(variant.replace(injected, ""), original)

    def test_snapshot_substitutions_use_exact_scope_inventory(self):
        plan = load_plan()
        snapshot = snapshot_sql(plan)
        self.assertNotIn("__RETIRED_", snapshot)
        self.assertIn("('programs')", snapshot)
        self.assertIn("capture(true)", snapshot)
        self.assertNotIn('__CATALOG_CAPTURE_SQL__', snapshot)
        self.assertIn(plan.sql('snapshots/catalog'), snapshot)

    def test_late_failure_rejects_duplicate_or_malformed_commit_lines_for_lf_and_crlf(self):
        for newline in ('\n', '\r\n'):
            for lines in (['BEGIN;', 'COMMIT;', 'COMMIT;', ''],
                          ['BEGIN;', 'COMMIT; trailing text', ''],
                          ['BEGIN;', r'COMMIT;\r', ''],
                          ['BEGIN;', 'COMMIT;']):
                with self.subTest(newline=repr(newline), lines=lines), self.assertRaises(HarnessError):
                    late_failure(newline.join(lines))

    def test_preparation_cli_never_calls_runtime_and_rejects_execution_flags(self):
        output = StringIO()
        with patch.object(sys, "argv", ["academic_setup", "--check"]), redirect_stdout(output):
            self.assertEqual(main(), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["preceding_migrations"], 45)
        self.assertIs(report["execution_authorized"], False)
        self.assertTrue(report["execution_blockers"])
        with patch.object(sys, "argv", ["academic_setup", "--execute"]), \
                patch("sys.stderr", StringIO()), self.assertRaises(SystemExit):
            main()
