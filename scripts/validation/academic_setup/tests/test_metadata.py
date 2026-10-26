from copy import deepcopy

from scripts.validation.academic_setup.metadata import validate_container
from scripts.validation.academic_setup.policy import DATA_DIRECTORY, HarnessError
from scripts.validation.academic_setup.tests.support import (
    CONTAINER, PINS, OfflineCase, container_metadata,
)


class MetadataTests(OfflineCase):
    def test_isolation_is_required_before_start_sql_and_cleanup(self):
        cases = {
            "wrong_id": lambda c: c.update(Id="3" * 64),
            "wrong_name": lambda c: c.update(Name="/supabase_db_CollegeAIChatbot"),
            "wrong_image": lambda c: c.update(Image="sha256:" + "3" * 64),
            "mutable_tag": lambda c: c["Config"].update(Image="postgres:latest"),
            "missing_labels": lambda c: c["Config"].update(Labels={}),
            "other_run": lambda c: c["Config"]["Labels"].update({"collegeai.validation.run": "a" * 32}),
            "other_purpose": lambda c: c["Config"]["Labels"].update({"collegeai.validation.purpose": "other"}),
            "other_harness": lambda c: c["Config"]["Labels"].update({"collegeai.validation.harness": "other"}),
            "network_mode": lambda c: c["HostConfig"].update(NetworkMode="bridge"),
            "attached_network": lambda c: c["NetworkSettings"].update(Networks={"bridge": {}}),
            "host_port": lambda c: c["HostConfig"].update(PortBindings={"5432/tcp": [{"HostPort": "5432"}]}),
            "runtime_port": lambda c: c["NetworkSettings"].update(Ports={"5432/tcp": [{"HostPort": "5432"}]}),
            "publish_all": lambda c: c["HostConfig"].update(PublishAllPorts=True),
            "bind": lambda c: c["HostConfig"].update(Binds=["/host:/data"]),
            "mount_request": lambda c: c["HostConfig"].update(Mounts=[{"Type": "bind"}]),
            "inherited_volume": lambda c: c["HostConfig"].update(VolumesFrom=["other"]),
            "persistent_mount": lambda c: c.update(Mounts=[{"Type": "volume", "Destination": DATA_DIRECTORY}]),
            "extra_mount": lambda c: c.update(Mounts=[{"Type": "bind", "Destination": "/elsewhere"}]),
            "extra_volume": lambda c: c["Config"].update(Volumes={"/elsewhere": {}}),
            "no_tmpfs": lambda c: c["HostConfig"].update(Tmpfs={}),
            "oversized_tmpfs": lambda c: c["HostConfig"]["Tmpfs"].update({DATA_DIRECTORY: "rw,size=1g"}),
            "extra_tmpfs": lambda c: c["HostConfig"]["Tmpfs"].update({"/extra": "rw,size=1"}),
            "wrong_pgdata": lambda c: c["Config"].update(Env=["PGDATA=/elsewhere"]),
            "duplicate_pgdata": lambda c: c["Config"]["Env"].append("PGDATA=/elsewhere"),
            "root_user": lambda c: c["Config"].update(User="0:0"),
            "image_entrypoint": lambda c: c["Config"].update(Entrypoint=["docker-entrypoint.sh"]),
            "wrong_command": lambda c: c["Config"].update(Cmd=["postgres"]),
            "no_autoremove": lambda c: c["HostConfig"].update(AutoRemove=False),
            "privileged": lambda c: c["HostConfig"].update(Privileged=True),
            "writable_root": lambda c: c["HostConfig"].update(ReadonlyRootfs=False),
            "added_capability": lambda c: c["HostConfig"].update(CapAdd=["SYS_ADMIN"]),
            "missing_cap_drop": lambda c: c["HostConfig"].update(CapDrop=[]),
            "unconfined": lambda c: c["HostConfig"].update(SecurityOpt=["seccomp=unconfined"]),
            "device": lambda c: c["HostConfig"].update(Devices=[{"PathOnHost": "/dev/sda"}]),
            "host_pid": lambda c: c["HostConfig"].update(PidMode="host"),
            "host_ipc": lambda c: c["HostConfig"].update(IpcMode="host"),
            "shared_userns": lambda c: c["HostConfig"].update(UsernsMode="host"),
            "missing_port_metadata": lambda c: c["NetworkSettings"].pop("Ports"),
            "missing_storage_metadata": lambda c: c["Config"].pop("Volumes"),
        }
        for name, mutate in cases.items():
            for action in ("start", "sql", "cleanup"):
                with self.subTest(case=name, action=action):
                    session, fake = self.session()
                    if action == "sql":
                        session.start()
                        fake.calls.clear()
                    mutate(fake.container)
                    with self.assertRaises(HarnessError):
                        if action == "sql":
                            session.sql("SELECT 1;")
                        else:
                            getattr(session, action)()
                    self.assertEqual(self.mutating_operations(fake), [])

    def test_all_missing_required_metadata_fails_closed(self):
        original = container_metadata("b" * 32)
        for group in (None, "Config", "HostConfig", "State", "NetworkSettings"):
            for key in (original if group is None else original[group]):
                with self.subTest(group=group, key=key):
                    candidate = deepcopy(original)
                    (candidate if group is None else candidate[group]).pop(key)
                    with self.assertRaises(HarnessError):
                        validate_container(candidate, CONTAINER, "b" * 32, PINS)

    def test_accepts_unpublished_image_port_and_mirrored_tmpfs(self):
        session, fake = self.session()
        fake.container["NetworkSettings"]["Ports"] = {"5432/tcp": None}
        fake.container["Mounts"] = [{"Type": "tmpfs", "Destination": DATA_DIRECTORY,
                                    "Source": "", "RW": True}]
        session.start()

    def test_full_id_is_required_even_when_labels_match(self):
        candidate = container_metadata("b" * 32)
        for identity in (CONTAINER[:12], "supabase_db_CollegeAIChatbot", "", None):
            with self.subTest(identity=identity), self.assertRaises(HarnessError):
                validate_container(candidate, identity, "b" * 32, PINS)
