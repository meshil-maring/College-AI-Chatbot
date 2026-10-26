from threading import Barrier
from unittest.mock import Mock

from scripts.validation.academic_setup.concurrency import pair_scripts, run_concurrency
from scripts.validation.academic_setup.inputs import load_plan
from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.tests.support import OfflineCase


class ConcurrencyTests(OfflineCase):
    def test_all_pairs_launch_two_overlapping_sessions_and_join_before_verification(self):
        plan = load_plan()
        barrier = Barrier(2)
        calls = []

        def sql(text):
            calls.append(text)
            if "SET LOCAL application_name=" in text:
                barrier.wait(timeout=2)

        run_concurrency(Mock(sql=sql), plan)
        self.assertEqual(calls[:2], [plan.sql('concurrency/setup'), plan.sql('concurrency/synchronization')])
        self.assertEqual(len([text for text in calls if 'SET LOCAL application_name=' in text]), 8)
        self.assertEqual(calls[-2:], [plan.sql('concurrency/verify'), plan.sql('concurrency/teardown')])

    def test_failing_pair_stops_before_later_lanes_and_verification(self):
        calls = []

        def fail(text):
            calls.append(text)
            if 'SET LOCAL application_name=' in text:
                raise HarnessError('Injected race failure')

        with self.assertRaisesRegex(HarnessError, 'race failure'):
            run_concurrency(Mock(sql=fail), load_plan())
        self.assertFalse(any('RACE_CHILD' in text or 'RACE_ROLLBACK' in text for text in calls))
        self.assertNotIn(load_plan().sql('concurrency/verify'), calls)

    def test_pair_contracts_prove_blocking_independence_and_rollback(self):
        for lane in ('duplicate', 'parent', 'independent', 'rollback'):
            left, right = pair_scripts(lane, 'abcdef123456')
            self.assertIn("race_wait('holder'", right)
            self.assertIn("race_wait('independent'" if lane == 'independent' else "race_wait('blocked'", left)
            self.assertIn("statement_timeout='20s'", left)
            self.assertTrue(left.endswith('ROLLBACK;' if lane == 'rollback' else 'COMMIT;'))
            self.assertTrue(right.endswith('COMMIT;'))
        self.assertIn("'23505'", pair_scripts('duplicate', 'abcdef')[1])
        self.assertIn("'23514','Active academic parents required'", pair_scripts('parent', 'abcdef')[1])
        self.assertIn("WHERE name='b'", pair_scripts('independent', 'abcdef')[1])
