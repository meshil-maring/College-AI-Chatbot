"""Unit tests for fail-closed disposable-target validation; no Docker/DB access."""
import json
import unittest
from unittest.mock import patch

import disposable_container as target

CONTAINER_ID = "a" * 64
RUN_TOKEN = "b" * 32
PURPOSE = "faculty-attendance"


def inspected_container(**overrides):
    value = {
        "Id": CONTAINER_ID,
        "State": {"Running": True},
        "Config": {
            "Image": target.EXPECTED_IMAGE,
            "Labels": {
                "collegeai.validation.disposable": "true",
                "collegeai.validation.run": RUN_TOKEN,
                "collegeai.validation.purpose": PURPOSE,
            },
        },
        "Mounts": [{"Type": "tmpfs", "Destination": "/var/lib/postgresql/data"}],
        "HostConfig": {
            "Binds": [],
            "Tmpfs": {"/var/lib/postgresql/data": "rw,size=536870912"},
            "AutoRemove": True,
            "PortBindings": {},
            "NetworkMode": "none",
        },
    }
    for key, value_override in overrides.items():
        value[key] = value_override
    return value


class DisposableTargetTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {"DOCKER_HOST": ""})
        self.env.start()
        self.addCleanup(self.env.stop)

    def call_with(self, container):
        responses = [
            type("Result", (), {"returncode": 0, "stdout": "desktop-linux\n"})(),
            type("Result", (), {"returncode": 0, "stdout": "docker-desktop\n"})(),
            type("Result", (), {"returncode": 0, "stdout": json.dumps([container])})(),
        ]
        with patch.object(target, "command", side_effect=responses):
            return target.validate_disposable_target(CONTAINER_ID, RUN_TOKEN, PURPOSE)

    def test_accepts_exact_isolated_run_owned_container(self):
        self.assertEqual(self.call_with(inspected_container()), CONTAINER_ID)

    def test_rejects_wrong_run_token(self):
        value = inspected_container()
        value["Config"]["Labels"]["collegeai.validation.run"] = "c" * 32
        with self.assertRaisesRegex(RuntimeError, "Run token"):
            self.call_with(value)

    def test_rejects_persistent_volume(self):
        value = inspected_container()
        value["Mounts"] = [{"Type": "volume", "Destination": "/var/lib/postgresql/data"}]
        with self.assertRaisesRegex(RuntimeError, "tmpfs"):
            self.call_with(value)

    def test_rejects_published_port(self):
        value = inspected_container()
        value["HostConfig"]["PortBindings"] = {"5432/tcp": [{"HostPort": "54322"}]}
        with self.assertRaisesRegex(RuntimeError, "published host ports"):
            self.call_with(value)

    def test_rejects_network_access(self):
        value = inspected_container()
        value["HostConfig"]["NetworkMode"] = "bridge"
        with self.assertRaisesRegex(RuntimeError, "network=none"):
            self.call_with(value)

    def test_rejects_arbitrary_id_before_inspection(self):
        with self.assertRaisesRegex(RuntimeError, "64-character"):
            target.validate_disposable_target("supabase_db_CollegeAIChatbot", RUN_TOKEN, PURPOSE)


if __name__ == "__main__":
    unittest.main()
