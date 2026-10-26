from contextlib import nullcontext
from dataclasses import replace
import os
from subprocess import CompletedProcess
from unittest.mock import patch

from scripts.validation.academic_setup import policy
from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.transport import Docker, LiveTransport
from scripts.validation.academic_setup.identity import config_digest
from scripts.validation.academic_setup.tests.support import OfflineCase, PINS


class PolicyTests(OfflineCase):
    def test_rejects_wrong_endpoint_before_io(self):
        for endpoint in ("tcp://example.invalid:2375", "unix:///var/run/docker.sock", ""):
            with self.subTest(endpoint=endpoint), self.assertRaises(HarnessError):
                Docker(replace(PINS, endpoint=endpoint))

    def test_rejects_incomplete_or_tag_image_pins(self):
        for value in ("sha256", "sha256:short", "postgres:17", None, "sha256:" + "A" * 64):
            with self.subTest(value=value), self.assertRaises(HarnessError):
                Docker(replace(PINS, image_id=value))

    def test_rejects_unreviewed_engine_executable_or_os_identity(self):
        cases = [dict(engine_id=""), dict(docker_executable="docker"),
                 dict(docker_executable="//remote/share/docker.exe"),
                 dict(docker_executable="C:/Docker/../bin/docker.exe"),
                 dict(postgres_uid=0), dict(postgres_gid=True), dict(postgres_uid=None)]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(HarnessError):
                Docker(replace(PINS, **values))

    def test_default_transport_is_sealed_without_spawning_process(self):
        with self.assertRaisesRegex(HarnessError, "offline review only"):
            Docker(PINS).preflight()

    def test_future_live_transport_strips_inherited_credentials_and_overrides(self):
        values = {"DOCKER_HOST": "tcp://remote", "PGHOST": "hosted.invalid",
                  "PGPASSWORD": "sentinel", "SUPABASE_URL": "https://hosted.invalid",
                  "HTTP_PROXY": "http://remote", "DOCKER_CONFIG": "private-source"}
        with patch.dict(os.environ, values), patch.object(policy, "EXECUTION_AUTHORIZED", True), \
                patch("tempfile.TemporaryDirectory", return_value=nullcontext("private-target")), \
                patch("subprocess.run", return_value=CompletedProcess([], 0, "", "")) as run:
            LiveTransport()([PINS.docker_executable, "--host", PINS.endpoint, "info"])
        argv = run.call_args.args[0]
        options = run.call_args.kwargs
        self.assertEqual(argv[1:3], ["--config", "private-target"])
        self.assertTrue(set(options["env"]) <= {"TEMP", "TMP", "SystemRoot", "WINDIR"})
        self.assertEqual(options["cwd"], "private-target")
        self.assertIs(options["shell"], False)

    def test_wrong_engine_or_image_prevents_creation(self):
        cases = [("engine", "ID", "other-engine-123456"),
                 ("engine", "Name", "remote"), ("engine", "OSType", "windows"),
                 ("engine", "Architecture", "arm64"),
                 ("image", "Id", "sha256:" + "3" * 64),
                 ("image", "RepoTags", ["postgres:latest"]),
                 ("image", "Os", "windows"), ("image", "Architecture", "arm64"),
                 ("image", "Config", {"Volumes": {"/persistent": {}}})]
        for group, key, value in cases:
            with self.subTest(group=group, key=key):
                session, fake = self.session(created=False)
                getattr(fake, group)[key] = value
                with self.assertRaises(HarnessError):
                    session.create()
                self.assertFalse(any(call[0][0] == "create" for call in fake.calls))

    def test_engine_and_image_are_rechecked_before_start(self):
        for group, key, value in (("engine", "ID", "other-engine-123456"),
                                  ("image", "Id", "sha256:" + "4" * 64)):
            with self.subTest(group=group):
                session, fake = self.session()
                getattr(fake, group)[key] = value
                with self.assertRaises(HarnessError):
                    session.start()
                self.assertEqual(self.mutating_operations(fake), [])

    def test_owned_labels_account_for_the_exact_approved_images_inherited_labels(self):
        session, fake = self.session(created=False)
        fake.image["Config"]["Labels"] = {"org.example.image": "synthetic"}
        session.docker.pins = replace(session.docker.pins,
                                     image_config_sha256=config_digest(fake.image["Config"]))
        session.create()
        session.start()
