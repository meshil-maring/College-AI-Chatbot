"""Offline regressions for startup status and operation deadlines."""
from contextlib import nullcontext
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

from scripts.validation.academic_setup import policy
from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.tests.support import OfflineCase, PINS
from scripts.validation.academic_setup.transport import LiveTransport


class ReadinessTests(OfflineCase):
    def test_no_response_then_ready_is_retried(self):
        session, fake = self.session(started=True)
        transport = fake.__call__
        statuses = iter((2, 0))
        sleeps = []

        def responding(arguments, **kwargs):
            if arguments[-1] == '1':
                fake.ready_code = next(statuses)
            return transport(arguments, **kwargs)

        session.docker.transport = responding
        session.ready(timeout=1, clock=lambda: 0, sleep=sleeps.append)
        self.assertEqual(sleeps, [0.1])
        self.assertFalse(session.readiness_pending)
        self.assertFalse(session.failed)

    def test_persistent_no_response_exhausts_deadline_and_blocks_sql(self):
        session, fake = self.session(started=True)
        fake.ready_code = 2
        now = [0]
        sleeps = []

        def sleep(seconds):
            sleeps.append(seconds)
            now[0] += seconds

        with self.assertRaisesRegex(HarnessError, 'deadline'):
            session.ready(timeout=0.25, clock=lambda: now[0], sleep=sleep)
        self.assertEqual(len(sleeps), 3)
        self.assertAlmostEqual(sum(sleeps), 0.25)
        self.assertTrue(session.failed)
        with self.assertRaises(HarnessError):
            session.sql('SELECT 1;')
        self.assertFalse(any(call[1] is not None for call in fake.calls))

    def test_invalid_readiness_status_is_fatal_without_sleep(self):
        session, fake = self.session(started=True)
        fake.ready_code = 3
        sleeps = []
        with self.assertRaisesRegex(HarnessError, 'readiness check failed'):
            session.ready(timeout=1, clock=lambda: 0, sleep=sleeps.append)
        self.assertEqual(sleeps, [])
        self.assertTrue(session.failed)
        self.assertTrue(session.readiness_pending)
        with self.assertRaises(HarnessError):
            session.sql('SELECT 1;')
        self.assertFalse(any(call[1] is not None for call in fake.calls))

    def test_each_readiness_operation_receives_remaining_budget(self):
        session, fake = self.session(started=True)
        fake.calls.clear()
        transport = fake.__call__
        now = [0]
        operations = []

        def bounded(arguments, **kwargs):
            operations.append(arguments[3])
            self.assertGreater(kwargs['timeout'], 0)
            self.assertLessEqual(kwargs['timeout'], 2-now[0])
            result = transport(arguments, **kwargs)
            now[0] += 0.1
            return result

        session.docker.transport = bounded
        session.ready(timeout=2, clock=lambda: now[0])
        self.assertEqual(operations, ['version', 'info', 'image', 'container', 'exec', 'exec'])
        self.assertEqual(len({call[2] for call in fake.calls}), 6)

    def test_late_sql_inspection_prevents_submission(self):
        session, fake = self.session(started=True)
        transport = fake.__call__
        now = [0]

        def late(arguments, **kwargs):
            result = transport(arguments, **kwargs)
            if arguments[3:5] == ['container', 'inspect']:
                now[0] = 121
            return result

        session.docker.transport = late
        with self.assertRaisesRegex(HarnessError, 'deadline'):
            session.sql('SELECT 1;', clock=lambda: now[0])
        self.assertFalse(any(call[1] is not None for call in fake.calls))

    def test_late_sql_completion_cannot_be_accepted(self):
        for code, state in ((0, None), (3, 'P4001')):
            with self.subTest(code=code):
                session, fake = self.session(started=True)
                transport = fake.__call__
                now = [0]

                def late(arguments, **kwargs):
                    if kwargs.get('input') is not None:
                        now[0] = 121
                        return CompletedProcess(arguments, code, 'late output', 'ERROR: P4001')
                    return transport(arguments, **kwargs)

                session.docker.transport = late
                with self.assertRaisesRegex(HarnessError, 'deadline'):
                    session.sql('negative or successful probe', expected_sqlstate=state,
                                clock=lambda: now[0])
                self.assertTrue(session.failed)
                with self.assertRaises(HarnessError):
                    session.sql('SELECT 2;')

    def test_late_process_creation_result_is_refused_by_live_adapter(self):
        now = [0]

        def checkpoint():
            if now[0] >= 1:
                raise HarnessError('Operation deadline exceeded')

        def completed(*args, **kwargs):
            now[0] = 2
            return CompletedProcess([], 0, '', '')

        with patch.object(policy, 'EXECUTION_AUTHORIZED', True), \
                patch('tempfile.TemporaryDirectory', return_value=nullcontext('synthetic-config')), \
                patch('subprocess.run', side_effect=completed):
            with self.assertRaisesRegex(HarnessError, 'deadline'):
                LiveTransport()([PINS.docker_executable, '--host', PINS.endpoint, 'info'],
                                checkpoint=checkpoint, budget=lambda: 1-now[0])

    def test_client_sql_timeout_never_claims_database_cancellation(self):
        session, fake = self.session(started=True)
        transport = fake.__call__

        def timed_out(arguments, **kwargs):
            if kwargs.get('input') is not None:
                raise TimeoutExpired(arguments, kwargs['timeout'])
            return transport(arguments, **kwargs)

        session.docker.transport = timed_out
        with self.assertRaisesRegex(HarnessError, 'outcome is unverified') as failure:
            session.sql('SELECT 1;')
        self.assertNotIn('cancel', str(failure.exception).lower())
        self.assertNotIn('rolled back', str(failure.exception).lower())
        self.assertTrue(session.failed)
        self.assertFalse(session.closed)
