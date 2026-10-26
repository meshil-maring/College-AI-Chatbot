from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.validation.academic_setup.identity import config_digest, validate_executable
from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.tests.support import OfflineCase, PINS
from scripts.validation.academic_setup.transport import Docker


class IdentityTests(OfflineCase):
    def test_every_missing_reviewed_pin_is_rejected_before_io(self):
        for key in ('image_id', 'engine_id', 'docker_executable', 'docker_client_version',
                    'docker_server_version', 'executable_sha256', 'image_config_sha256', 'bootstrap_sha256'):
            with self.subTest(key=key), self.assertRaises(HarnessError):
                Docker(replace(PINS, **{key: ''}))

    def test_client_server_and_bootstrap_configuration_changes_prevent_creation(self):
        for kind in ('client', 'server', 'user', 'entrypoint', 'command', 'bootstrap'):
            session, fake = self.session(created=False)
            if kind in ('client', 'server'):
                fake.version[kind.title()]['Version'] = '99.0.0'
            elif kind == 'bootstrap':
                session.docker.pins = replace(PINS, bootstrap_sha256='b'*64)
            else:
                key = {'user': 'User', 'entrypoint': 'Entrypoint', 'command': 'Cmd'}[kind]
                fake.image['Config'][key] = 'changed'
            with self.subTest(kind=kind), self.assertRaises(HarnessError):
                session.create()
            self.assertFalse(any(call[0][0] == 'create' for call in fake.calls))

    def test_executable_hash_and_linked_path_are_rejected(self):
        metadata = Mock(st_mode=0o100755, st_file_attributes=0)
        with patch.object(Path, 'lstat', return_value=metadata), \
                patch.object(Path, 'is_file', return_value=True), \
                patch.object(Path, 'read_bytes', return_value=b'changed docker.exe'):
            with self.assertRaisesRegex(HarnessError, 'fingerprint'):
                validate_executable(PINS)
        metadata.st_file_attributes = 1024
        with patch.object(Path, 'lstat', return_value=metadata), self.assertRaisesRegex(HarnessError, 'Linked'):
            validate_executable(PINS)

    def test_config_digest_is_complete_and_order_independent(self):
        self.assertEqual(config_digest({'Cmd': [], 'User': 'postgres'}),
                         config_digest({'User': 'postgres', 'Cmd': []}))
        self.assertNotEqual(config_digest({'User': 'postgres'}), config_digest({'User': 'root'}))
