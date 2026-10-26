from contextlib import contextmanager
from unittest.mock import patch

from scripts.validation.academic_setup import policy
from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.transport import LiveTransport
from scripts.validation.academic_setup.tests.support import CONTAINER, OfflineCase, PINS


class DeadlineCleanupTests(OfflineCase):
    def test_late_private_config_setup_cannot_submit_a_process(self):
        now = [0]

        @contextmanager
        def delayed_directory(**kwargs):
            now[0] = 2
            yield 'synthetic-private-config'

        def checkpoint():
            if now[0] >= 1:
                raise HarnessError('SQL deadline exceeded')

        with patch.object(policy, 'EXECUTION_AUTHORIZED', True), \
                patch('tempfile.TemporaryDirectory', delayed_directory), patch('subprocess.run') as run:
            with self.assertRaisesRegex(HarnessError, 'deadline'):
                LiveTransport()([PINS.docker_executable, '--host', PINS.endpoint, 'exec'],
                                checkpoint=checkpoint, budget=lambda: 1-now[0])
            run.assert_not_called()

    def test_sql_cannot_cross_deadline_while_executable_fingerprint_is_checked(self):
        session, fake = self.session(started=True)
        session.docker.transport = LiveTransport()
        now = [0]
        validations = [0]

        def fingerprint(_):
            validations[0] += 1
            if validations[0] == 6:  # Four inspections, runtime identity, then psql.
                now[0] = 121

        with patch.object(policy, 'EXECUTION_AUTHORIZED', True), \
                patch('scripts.validation.academic_setup.transport.validate_executable', side_effect=fingerprint), \
                patch.object(LiveTransport, '__call__', side_effect=lambda args, **kwargs:
                             fake(args, input=kwargs.get('input'), timeout=kwargs['timeout'])):
            with self.assertRaisesRegex(HarnessError, 'deadline'):
                session.sql('SELECT 1;', clock=lambda: now[0])
        self.assertEqual(validations[0], 6)
        self.assertFalse(any(call[1] is not None for call in fake.calls))

    def test_prerequisite_rejection_requires_exact_message_as_well_as_sqlstate(self):
        for message, accepted in (('Reviewed prerequisite refusal', True), ('Other error', False)):
            session, fake = self.session(started=True)
            fake.sql_results = [(3, '', 'ERROR: P0001: ' + message + '\nCONTEXT: test')]
            if accepted:
                session.sql('negative probe', expected_sqlstate='P0001',
                            expected_message='Reviewed prerequisite refusal')
            else:
                with self.assertRaisesRegex(HarnessError, 'rejection message'):
                    session.sql('negative probe', expected_sqlstate='P0001',
                                expected_message='Reviewed prerequisite refusal')

    def test_late_success_at_each_blocking_readiness_step_fails_closed(self):
        for operation in ('version', 'info', 'image', 'container', 'pg_isready', 'runtime'):
            with self.subTest(operation=operation):
                session, fake = self.session(started=True)
                now = [0]
                transport = fake.__call__

                def blocking(arguments, **kwargs):
                    result = transport(arguments, **kwargs)
                    args = arguments[3:]
                    match = (args[0] == operation or operation == 'pg_isready' and args[-1] == '1'
                             or operation == 'runtime' and '-ceu' in args)
                    if match:
                        now[0] = 2
                    return result

                session.docker.transport = blocking
                fake.calls.clear()
                with self.assertRaisesRegex(HarnessError, 'deadline'):
                    session.ready(timeout=1, clock=lambda: now[0], sleep=lambda _: None)
                self.assertTrue(session.failed)
                self.assertFalse(any(call[1] is not None for call in fake.calls))
                with self.assertRaises(HarnessError):
                    session.sql('SELECT 1;')
                operations = [call[0][0] for call in fake.calls]
                if operation in ('version', 'info', 'image', 'container'):
                    self.assertEqual(operations[-1], operation)
                    self.assertNotIn('exec', operations)

    def test_sql_rechecks_deadline_after_inspection_and_immediately_before_submission(self):
        for expiry in (2, 7, 8):
            with self.subTest(expiry=expiry):
                session, fake = self.session(started=True)
                ticks = [0]

                def clock():
                    ticks[0] += 1
                    return 121 if ticks[0] >= expiry else 0

                with self.assertRaisesRegex(HarnessError, 'deadline'):
                    session.sql('SELECT 1;', clock=clock)
                self.assertFalse(any(call[1] is not None for call in fake.calls))
                self.assertTrue(session.failed)

    def test_runtime_identity_mismatch_prevents_sql(self):
        for identity in ('', '0\n0\n', '999\n999\n0:0:0:0\n999:999:999:999\n'):
            session, fake = self.session(started=True)
            fake.runtime_identity = identity
            with self.assertRaisesRegex(HarnessError, 'runtime identity'):
                session.sql('SELECT 1;')
            self.assertFalse(any(call[1] is not None for call in fake.calls))

    def test_confirmed_ready_may_be_followed_by_sql_after_readiness_window(self):
        session, fake = self.session(started=True)
        session.ready(timeout=1, clock=lambda: 0)
        session.sql('SELECT 1;')
        self.assertFalse(session.failed)

    def test_removal_is_confirmed_by_successful_exact_full_id_query(self):
        for started in (False, True):
            session, fake = self.session(started=started)
            session.cleanup()
            self.assertTrue(session.closed)
            self.assertEqual(fake.calls[-1][0], ['container', 'ls', '--all', '--no-trunc',
                '--filter', f'id={CONTAINER}', '--format', '{{.ID}}'])

    def test_surviving_or_unqueryable_target_never_closes_session(self):
        for failure in ('present', 'timeout', 'engine'):
            session, fake = self.session(started=True)
            fake.removal_confirmed = False
            if failure == 'timeout':
                original = session.docker.call

                def fail_query(*args, **kwargs):
                    if args[:2] == ('container', 'ls'):
                        raise HarnessError('Removal unverified')
                    return original(*args, **kwargs)

                session.docker.call = fail_query
            elif failure == 'engine':
                original = fake.__call__

                def change_engine(arguments, **kwargs):
                    result = original(arguments, **kwargs)
                    if arguments[3] == 'stop':
                        fake.engine['ID'] = 'changed-engine-123456'
                    return result

                session.docker.transport = change_engine
            with self.assertRaises(HarnessError):
                session.cleanup()
            self.assertFalse(session.closed)
            self.assertEqual(sum(call[0][0] == 'stop' for call in fake.calls), 1)
