from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.tests.support import CONTAINER, IMAGE, OfflineCase


class SessionTests(OfflineCase):
    def test_psql_prefix_cannot_hide_another_state_context_or_error_record(self):
        for newline in ('\n', '\r\n'):
            for error in (
                'psql:<stdin>:7: ERROR: 23505: ERROR: P0001: Reviewed refusal',
                'psql:<stdin>:7: CONTEXT: ERROR: P0001: Reviewed refusal',
                'psql:<stdin>:7: 23505: ERROR: P0001: Reviewed refusal',
                'psql:<stdin>:7: ERROR: P0001: Reviewed refusal'+newline+'ERROR: 23505: Other',
                'psql:<stdin>:7: ERROR: P0001: Reviewed refusal'+newline+'ERROR: malformed',
                'psql:<stdin>:7: ERROR: P0001: Reviewed refusal'+newline+'ERROR: P0001: Reviewed refusal',
                'psql:<stdin>:7:'+newline+'ERROR: P0001: Reviewed refusal',
                'psql:<stdin>:seven: ERROR: P0001: Reviewed refusal',
                'ERROR: 23505: wrong\vERROR: P0001: Reviewed refusal',
            ):
                with self.subTest(newline=repr(newline), error=error):
                    session, fake = self.session(started=True)
                    fake.sql_results = [(3, '', error+newline)]
                    with self.assertRaises(HarnessError):
                        session.sql('negative probe', expected_sqlstate='P0001', expected_message='Reviewed refusal')
                    self.assertTrue(session.failed)

    def test_real_psql_error_location_and_verbose_context_are_unambiguous(self):
        for newline in ('\n', '\r\n'):
            session, fake = self.session(started=True)
            fake.sql_results = [(3, '', newline.join([
                'psql:<stdin>:2: NOTICE: fixture already exists, skipping',
                'psql:<stdin>:3: WARNING: synthetic fixture warning',
                'psql:<stdin>:123: ERROR:  P0001: Reviewed refusal',
                'CONTEXT: PL/pgSQL function inline_code_block line 1 at RAISE',
                'LOCATION: exec_stmt_raise, pl_exec.c:3920', '',
            ]))]
            session.sql('negative probe', expected_sqlstate='P0001', expected_message='Reviewed refusal')
            self.assertFalse(session.failed)

    def test_expected_error_message_accepts_lf_crlf_and_psql_prefix(self):
        message = 'Reviewed refusal: exact (fixture) [1].'
        for newline in ('\n', '\r\n'):
            for prefix in ('', 'psql:<stdin>:7: '):
                with self.subTest(newline=repr(newline), prefix=prefix):
                    session, fake = self.session(started=True)
                    fake.sql_results = [(3, '', prefix+'ERROR:  P0001: '+message+newline+'CONTEXT: fixture'+newline)]
                    session.sql('negative probe', expected_sqlstate='P0001', expected_message=message)
                    self.assertFalse(session.failed)

    def test_expected_error_rejects_wrong_or_split_message_and_literal_escapes(self):
        for newline in ('\n', '\r\n'):
            for error in ('ERROR: P0001: Wrong message', 'ERROR: P0001: Reviewed refusal extra',
                          'ERROR: P0001:'+newline+'Reviewed refusal',
                          'CONTEXT: ERROR: P0001: Reviewed refusal',
                          r'ERROR: P0001: Reviewed refusal\r',
                          'ERROR: P0001_suffix: Reviewed refusal'):
                with self.subTest(error=error, newline=repr(newline)):
                    session, fake = self.session(started=True)
                    fake.sql_results = [(3, '', error+newline)]
                    with self.assertRaises(HarnessError):
                        session.sql('negative probe', expected_sqlstate='P0001', expected_message='Reviewed refusal')
                    self.assertTrue(session.failed)

    def test_create_is_separate_from_start_and_forces_isolation(self):
        session, fake = self.session()
        create = next(call[0] for call in fake.calls if call[0][0] == "create")
        self.assertIn("--pull=never", create)
        self.assertEqual(create[create.index("--network") + 1], "none")
        self.assertIn("size=536870912", create[create.index("--tmpfs") + 1])
        self.assertIn(IMAGE, create)
        for forbidden in ("-p", "-P", "--publish", "--publish-all", "-v", "--volume", "--mount", "--env-file"):
            self.assertNotIn(forbidden, create)
        self.assertEqual(self.mutating_operations(fake), [])
        self.assertEqual(session.container_id, CONTAINER)
        self.assertEqual(len(session.token), 32)
        with self.assertRaises(HarnessError):
            session.create()

    def test_run_tokens_are_fresh(self):
        first, _ = self.session(created=False)
        second, _ = self.session(created=False)
        self.assertNotEqual(first.token, second.token)

    def test_sql_is_socket_only_and_preserves_file_transaction_boundaries(self):
        session, fake = self.session(started=True)
        script = "BEGIN;\nSELECT 1;\nCOMMIT;\n"
        session.sql(script)
        command, payload, timeout = next(call for call in fake.calls if call[1] is not None)
        self.assertEqual(payload, script)
        self.assertEqual(command[-2:], ["-f", "-"])
        self.assertIn("-X", command)
        self.assertIn("ON_ERROR_STOP=1", command)
        self.assertIn("--no-password", command)
        self.assertIn(CONTAINER, command)
        self.assertNotIn("--single-transaction", command)
        self.assertNotIn("-1", command)
        self.assertNotIn("-c", command)
        self.assertGreater(timeout, 0)
        self.assertLessEqual(timeout, 120)

    def test_timeout_and_sql_failure_poison_session_but_allow_validated_cleanup(self):
        for failure in ("timeout", "sql"):
            with self.subTest(failure=failure):
                session, fake = self.session(started=True)
                if failure == "timeout":
                    fake.timeout = "exec"
                else:
                    fake.sql_results = [(3, "secret-output", "secret-error")]
                with self.assertRaises(HarnessError) as raised:
                    session.sql("SELECT 1;")
                self.assertNotIn("secret", str(raised.exception))
                self.assertIsNone(raised.exception.__cause__)
                before = len(fake.calls)
                with self.assertRaisesRegex(HarnessError, "Session has failed"):
                    session.sql("SELECT 2;")
                self.assertEqual(len(fake.calls), before)
                fake.timeout = None
                session.cleanup()
                self.assertIn(["stop", "--time", "10", CONTAINER], [call[0] for call in fake.calls])
                self.assertTrue(session.closed)

    def test_expected_failure_requires_exact_psql_error_status_and_sqlstate(self):
        for result, accepted in (((3, "", "ERROR: P4001"), True),
                                 ((0, "", "ERROR: P4001"), False),
                                 ((1, "", "ERROR: P4001"), False),
                                 ((3, "", "ERROR: 23503"), False)):
            with self.subTest(result=result):
                session, fake = self.session(started=True)
                fake.sql_results = [result]
                if accepted:
                    session.sql("negative probe", expected_sqlstate="P4001")
                    self.assertFalse(session.failed)
                else:
                    with self.assertRaises(HarnessError):
                        session.sql("negative probe", expected_sqlstate="P4001")
                    self.assertTrue(session.failed)

    def test_cleanup_of_fresh_container_uses_full_id_without_force(self):
        session, fake = self.session()
        session.cleanup()
        self.assertIn(["rm", CONTAINER], [call[0] for call in fake.calls])
        self.assertEqual(fake.calls[-1][0][:2], ["container", "ls"])
        with self.assertRaises(HarnessError):
            session.cleanup()

    def test_create_timeout_never_guesses_name_or_target_for_cleanup(self):
        session, fake = self.session(created=False)
        fake.timeout = "create"
        with self.assertRaises(HarnessError):
            session.create()
        self.assertIsNone(session.container_id)
        with self.assertRaisesRegex(HarnessError, "manual review"):
            session.cleanup()
        self.assertFalse(any(call[0][0] in {"ls", "ps", "start", "stop", "rm"} for call in fake.calls))

    def test_preflight_failure_does_not_claim_create_was_submitted(self):
        session, fake = self.session(created=False)
        fake.fail = "info"
        with self.assertRaises(HarnessError):
            session.create()
        session.cleanup()
        self.assertFalse(session.create_submitted)

    def test_cleanup_timeout_is_unverified_and_not_retried(self):
        session, fake = self.session(started=True)
        fake.timeout = "stop"
        with self.assertRaisesRegex(HarnessError, "unverified"):
            session.cleanup()
        self.assertFalse(session.closed)
        self.assertEqual(sum(call[0][0] == "stop" for call in fake.calls), 1)

    def test_readiness_is_bounded_and_never_runs_sql_on_timeout(self):
        session, fake = self.session(started=True)
        fake.ready_code = 1
        ticks = iter([0, 0.1, 0.5, 1.1])
        with self.assertRaisesRegex(HarnessError, "deadline"):
            session.ready(timeout=1, clock=lambda: next(ticks), sleep=lambda _: None)
        self.assertTrue(session.failed)
        self.assertFalse(any(call[1] is not None for call in fake.calls))

    def test_stopped_or_unavailable_container_prevents_sql(self):
        session, fake = self.session()
        with self.assertRaises(HarnessError):
            session.sql("SELECT 1;")
        self.assertFalse(any(call[0][0] == "exec" for call in fake.calls))
