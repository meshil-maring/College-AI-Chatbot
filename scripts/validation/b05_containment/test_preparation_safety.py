"""Offline preparation checks only; never call main/preparation_plan or execute SQL."""
import ctypes
import re
import stat
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import prepare


class PathSafetyTests(unittest.TestCase):
    def test_external_and_ambiguous_paths_are_denied_before_metadata_access(self):
        values = (
            "C:/outside.sql", "C:outside.sql", "//server/share/file.sql",
            "\\\\server\\share\\file.sql", "\\\\?\\C:\\file.sql", "\\\\.\\pipe\\name",
            "/outside.sql", "\\outside.sql", "../outside.sql", "a/../outside.sql",
            "a/./file.sql", "a//file.sql", "a/", "a\\file.sql",
            "https://example.invalid/file.sql", "file://server/file.sql",
            "a/file.sql:stream", "a/file.sql.", "a/file.sql ", "NUL.sql",
            "a/COM1.txt", "a/LPT9", "a/file\x00.sql", "a/file\n.sql", "", None,
        )
        with patch.object(prepare, "require_local_drive") as drive, patch.object(Path, "lstat") as metadata:
            for value in values:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    prepare.local_file(value)
            drive.assert_not_called()
            metadata.assert_not_called()

    def test_component_walk_stops_before_traversing_reparse_target(self):
        root = Path("F:/repository")
        # Test drive root, repository ancestor, nested directory and final file.
        for bad in (Path(root.anchor), root, root / "safe", root / "safe/file.sql"):
            visited = []
            def metadata(path):
                visited.append(path)
                final = path == root / "safe/file.sql"
                return SimpleNamespace(
                    st_mode=stat.S_IFREG if final else stat.S_IFDIR,
                    st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT if path == bad else 0,
                )
            with self.subTest(bad=bad), patch.object(prepare, "REPOSITORY", root), \
                    patch.object(prepare, "require_local_drive"), \
                    patch.object(Path, "lstat", metadata), \
                    patch.object(Path, "resolve", side_effect=AssertionError("resolution reached")):
                with self.assertRaisesRegex(ValueError, "Reparse"):
                    prepare.local_file("safe/file.sql")
                self.assertEqual(visited[-1], bad)

    def test_symlink_is_denied_even_without_windows_attribute(self):
        info = SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
        with patch.object(prepare, "require_local_drive"), patch.object(Path, "lstat", return_value=info):
            with self.assertRaisesRegex(ValueError, "symbolic"):
                prepare.local_file("safe/file.sql")

    def test_checked_regular_file_and_directory_do_not_resolve(self):
        root = Path("F:/repository")
        target = root / "safe/file.sql"
        visited = []
        def metadata(path):
            visited.append(path)
            return SimpleNamespace(st_mode=stat.S_IFREG if path == target else stat.S_IFDIR,
                                   st_file_attributes=0)
        with patch.object(prepare, "REPOSITORY", root), patch.object(prepare, "require_local_drive"), \
                patch.object(Path, "lstat", metadata), \
                patch.object(Path, "resolve", side_effect=AssertionError("resolution reached")):
            self.assertEqual(prepare.local_file("safe/file.sql"), target)
            self.assertEqual(prepare.checked_path("safe", directory=True), root / "safe")
            self.assertEqual(visited[:4], [Path(root.anchor), root, root / "safe", target])

    def test_non_directory_ancestor_and_non_regular_file_are_denied(self):
        for mode in (stat.S_IFREG, stat.S_IFIFO):
            with self.subTest(mode=mode), patch.object(prepare, "require_local_drive"), \
                    patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=mode, st_file_attributes=0)):
                with self.assertRaisesRegex(ValueError, "path type"):
                    prepare.local_file("safe/file.sql")
        root = Path("F:/repository")
        with patch.object(prepare, "REPOSITORY", root), patch.object(prepare, "require_local_drive"), \
                patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=stat.S_IFDIR, st_file_attributes=0)):
            with self.assertRaisesRegex(ValueError, "path type"):
                prepare.local_file("safe/file.sql")

    def test_missing_local_component_fails_without_resolution(self):
        with patch.object(prepare, "require_local_drive"), \
                patch.object(Path, "lstat", side_effect=FileNotFoundError), \
                patch.object(Path, "resolve", side_effect=AssertionError("resolution reached")):
            with self.assertRaises(FileNotFoundError):
                prepare.local_file("safe/file.sql")

    def test_remote_unknown_and_removable_drive_types_fail_before_lstat(self):
        for kind in (0, 1, 2, 4, 5):
            drive_type = Mock(return_value=kind)
            with self.subTest(kind=kind), patch.object(ctypes, "WinDLL", return_value=SimpleNamespace(GetDriveTypeW=drive_type)), \
                    patch.object(Path, "lstat") as metadata:
                with self.assertRaisesRegex(ValueError, "repository drives"):
                    prepare.local_file("safe/file.sql")
                drive_type.assert_called_once_with(prepare.REPOSITORY.anchor)
                metadata.assert_not_called()

    def test_unc_or_drive_relative_repository_is_denied_before_windows_api(self):
        for root in (Path("//server/share/repository"), Path("F:repository")):
            with self.subTest(root=root), patch.object(prepare, "REPOSITORY", root), \
                    patch.object(ctypes, "WinDLL") as api, patch.object(Path, "lstat") as metadata:
                with self.assertRaisesRegex(ValueError, "local Windows"):
                    prepare.local_file("safe/file.sql")
                api.assert_not_called()
                metadata.assert_not_called()


class FixtureSafetyTests(unittest.TestCase):
    def test_pending_emails_are_unique_and_staff_has_matching_synthetic_identity(self):
        # Read fixed local source text only; no SQL parser/client or execution.
        sql = Path(__file__).with_name("fixtures_pre_b05.sql").read_text(encoding="utf-8")
        institutions = sql.split("INSERT INTO public.platform_admin_invitations", 1)[1].split(
            "INSERT INTO public.platform_super_admin_invitations", 1)[0]
        rows = re.findall(r"\((\d+),'([^']+)','([^']+)','([^']+)'\)", institutions)
        self.assertEqual(len(rows), 7)
        pending = [email.lower() for _, email, _, state in rows if state == "invited"]
        self.assertEqual(len(pending), len(set(pending)))  # Same tenant, any role.
        staff = next(row for row in rows if row[0] == "6")
        self.assertEqual(staff, ("6", "staff-recipient", "staff", "invited"))
        auth = sql.split("INSERT INTO auth.users", 1)[1].split("INSERT INTO public.users", 1)[0]
        self.assertIn("(12,'staff-recipient')", auth)
        requests = sql.split("INSERT INTO public.institution_membership_requests", 1)[1].split(
            "INSERT INTO public.students", 1)[0]
        self.assertIn("(6,12,'staff','approved')", requests)
        self.assertIn("label || '@example.invalid'", auth)
        self.assertIn("email || '@example.invalid'", institutions)
        for fixture in ("fixtures_pre_b05.sql", "fixtures_post_b05.sql"):
            text = Path(__file__).with_name(fixture).read_text(encoding="utf-8")
            domains = re.findall(r"@([A-Za-z0-9.-]+)", text)
            self.assertTrue(domains)
            self.assertEqual(set(domains), {"example.invalid"})


class TargetedOracleSourceTests(unittest.TestCase):
    """Stage 1.12 source consistency only; never execute SQL or a runtime case."""

    @classmethod
    def setUpClass(cls):
        cls.package = Path(__file__).parent
        cls.root = cls.package.parents[2]
        cls.matrix = (cls.package / "test_matrix.md").read_text(encoding="utf-8")
        cls.migrations = cls.root / "supabase/migrations"

    def source(self, filename):
        return (self.migrations / filename).read_text(encoding="utf-8")

    def test_outbox_projection_matches_schema_and_terminal_write_set(self):
        # Worker:7-51/112-128 and webhook:6-10 define actual fields/effects.
        worker = self.source("20261002000000_phase_7_17_email_outbox_worker.sql")
        webhook = self.source("20261002010000_phase_7_18_mailgun_webhook_reconciliation.sql")
        schema = worker.split('CREATE TABLE IF NOT EXISTS "public"."email_outbox" (', 1)[1]
        schema = schema.split('    CONSTRAINT ', 1)[0]
        fields = re.findall(r'^    "([a-z_]+)" ', schema, re.M)
        fields += re.findall(r'ADD COLUMN IF NOT EXISTS "([a-z_]+)"', webhook.split("CREATE UNIQUE INDEX", 1)[0])
        documented = re.search(r'`(id, message_type, aggregate_type, aggregate_id, [^`]+)`', self.matrix).group(1)
        self.assertEqual(documented.split(", "), fields)
        self.assertNotIn("version", fields)
        trigger = worker.split('CREATE OR REPLACE FUNCTION "public"."phase717_cancel_terminal_invitation_email"()', 1)[1]
        trigger = trigger.split("END;", 1)[0]
        assignments = trigger.split("SET ", 1)[1].split("WHERE ", 1)[0]
        self.assertEqual(set(re.findall(r'"([a-z_]+)"\s*=', assignments)),
                         {"status", "locked_at", "protected_token", "updated_at", "last_error_category"})
        self.assertIn('AND "status" = \'pending\'::text', trigger)
        self.assertIn("INVITATION_TERMINAL", trigger)
        oracle = self.matrix.split("**OB12-T:", 1)[1].split("**OB12-C:", 1)[0]
        self.assertIn("attempt_count", oracle)
        self.assertIn("delivery_sequence", oracle)
        self.assertIn("processing row and its attempt intact", oracle)
        self.assertIn("historical terminal", oracle)
        self.assertIn("zero row-count delta alone", self.matrix)
        register = self.matrix.split("**OB12 affected-case register.**", 1)[1].split("## Stage 1.12 C12", 1)[0]
        rows = [line for line in register.splitlines() if re.match(r'^\| OB12/M\d{2} \|', line)]
        self.assertEqual([line.split("|")[1].strip().split("/")[1] for line in rows], [f"M{i:02}" for i in range(1, 22)])
        self.assertTrue(all(line.endswith("| NOT RUN |") for line in rows))

    def test_cancellation_timestamp_contract_tracks_kind_specific_constraints(self):
        # Institution CHECK:66-91; platform schema:8-29 has no such CHECK.
        institution = self.source("20261001020000_phase_7_14_super_admin_university_admin_lifecycle.sql")
        platform = self.source("20261008000000_phase_9_super_admin_invitations.sql")
        b05 = self.source("20261017000000_b05_invitation_acceptance_security.sql")
        check = institution.split('CONSTRAINT "platform_admin_invitations_terminal_state_check"', 1)[1].split("\n);", 1)[0]
        self.assertIn('"cancelled_at" IS NOT NULL', check)
        self.assertIn('"accepted_at" IS NULL', check)
        self.assertNotIn("terminal_state_check", platform)
        routing = b05.split("CREATE FUNCTION public.b05_guard_invitation_acceptance()", 1)[1].split("END;", 1)[0]
        terminal_fields = routing.split("IF OLD.status <> 'invited'", 1)[1].split("THEN", 1)[0]
        self.assertNotIn("cancelled_at", terminal_fields)
        lifecycle = b05.split("CREATE FUNCTION public.b05_transition_invitation(", 1)[1].split("END;", 1)[0]
        self.assertIn("cancelled_at = CASE WHEN p_status = 'cancelled' THEN clock_timestamp()", lifecycle)
        self.assertLess(lifecycle.index("IF NOT v_repeat THEN"), lifecycle.index("cancelled_at = CASE"))
        contract = self.matrix.split("## Stage 1.12 C12", 1)[1].split("## Stage 1.12 T19", 1)[0]
        for statement in ("cancelled_at=Tcancel", "validated fixture_anchor", "platform_admin_invitations_terminal_state_check",
                          "platform schema has no equivalent timestamp CHECK", "preserves the exact returned timestamp",
                          "does not prohibit changing cancelled_at alone", "institution updated_at unchanged"):
            self.assertIn(statement, contract)
        additions = self.source("20261001030000_phase_7_15_invitation_delivery_email_verification.sql")
        self.assertIn('ADD COLUMN IF NOT EXISTS "last_sent_at"', additions)
        self.assertIn("email_delivery_at/last_sent_at NULL", contract)

    def test_wrong_tenant_controls_bind_valid_actor_and_distinct_resource_scope(self):
        # Fixture grants + phase81 guard ordering distinguish scope from claim denial.
        fixture = (self.package / "fixtures_pre_b05.sql").read_text(encoding="utf-8")
        for grant in ("(2,'admin','institution',1)", "(3,'admin','institution',2)", "(6,'staff','institution',2)"):
            self.assertIn(grant, fixture)
        self.assertIn("(4,6,'staff','pending')", fixture)
        phase81 = self.source("20261006000000_phase_8_1_scoped_rbac_and_faculty_assignments.sql")
        guard = phase81.split('CREATE OR REPLACE FUNCTION "public"."phase81_assert_institution_admin"(', 1)[1].split("END;", 1)[0]
        self.assertIn('"ur"."scope_id" = "p_institution_id"', guard)
        self.assertIn("Phase 8.1: active institution administrator required", guard)
        self.assertFalse(re.search(r'\b(INSERT|UPDATE|DELETE)\b', guard))
        b05 = self.source("20261017000000_b05_invitation_acceptance_security.sql")
        for start in ('CREATE OR REPLACE FUNCTION "public"."phase723_approve_membership_and_grant_role"(',
                      'CREATE FUNCTION public.b05_reject_membership('):
            body = b05.split(start, 1)[1].split("END;", 1)[0]
            self.assertLess(body.index("phase81_assert_institution_admin"), body.index("SELECT * INTO"))
        contract = self.matrix.split("## Stage 1.12 T19", 1)[1]
        for statement in ("RB=R(4)", "from A/OA to B/OB", "exactly the active 'admin'",
                          "immediate(RB,B,U(2),reason)", "reject(RB,B,U(2),reason)",
                          "Both expect42501", "auth_security_events delta0",
                          "immediate(R(1),B,U(3),reason)", "reject(R(1),B,U(3),reason)"):
            self.assertIn(statement, contract)


if __name__ == "__main__":
    unittest.main()
