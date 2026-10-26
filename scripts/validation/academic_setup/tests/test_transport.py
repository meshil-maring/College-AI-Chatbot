from subprocess import CompletedProcess
from unittest.mock import Mock

from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.transport import Docker
from scripts.validation.academic_setup.tests.support import OfflineCase, PINS


class TransportTests(OfflineCase):
    def test_malformed_or_ambiguous_inspection_responses_fail_closed(self):
        for payload in ("invalid-json", "[]", "[{},{}]", "[null]", "{}", '"text"'):
            with self.subTest(payload=payload):
                transport = lambda *args, **kwargs: CompletedProcess([], 0, payload, "")
                docker = Docker(PINS, transport)
                with self.assertRaises(HarnessError):
                    docker.object("container", "inspect", "2" * 64, singleton=True)

    def test_invalid_time_limits_are_rejected_before_transport(self):
        for timeout in (0, -1, 121, None, True):
            with self.subTest(timeout=timeout):
                transport = Mock()
                docker = Docker(PINS, transport)
                with self.assertRaises(HarnessError):
                    docker.call("info", timeout=timeout)
                transport.assert_not_called()

    def test_transport_failures_never_expose_stdout_stderr_or_command(self):
        for exception in (OSError("private-environment"), UnicodeError("private-environment")):
            with self.subTest(exception=type(exception).__name__):
                def unavailable(*args, **kwargs):
                    raise exception
                with self.assertRaises(HarnessError) as raised:
                    Docker(PINS, unavailable).preflight()
                self.assertNotIn("private-environment", str(raised.exception))
                self.assertTrue(raised.exception.__suppress_context__)
