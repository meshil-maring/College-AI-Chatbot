from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import runpy
from unittest.mock import Mock, patch

from scripts.validation.academic_setup import inputs
from scripts.validation.academic_setup.inputs import ACADEMIC, LEGACY_FIXTURE, load_plan, safe_sql
from scripts.validation.academic_setup.policy import HarnessError
from scripts.validation.academic_setup.tests.support import OfflineCase


class InputTests(OfflineCase):
    def test_exact_45_plus_four_pinned_migrations_and_synthetic_fixture(self):
        plan = load_plan()
        self.assertEqual(len(plan.migrations), 49)
        self.assertEqual(tuple(Path(item.path).name for item in plan.migrations[45:]), ACADEMIC)
        self.assertIn(LEGACY_FIXTURE, plan.inputs)
        self.assertEqual(len(plan.retired_tables), 39)
        self.assertEqual(len(plan.retired_functions), 71)
        for item in plan.migrations:
            self.assertEqual(sha256(inputs.local_file(item.path).read_bytes()).hexdigest(), item.digest)

    def test_changed_pinned_fixture_is_refused_without_sql_or_subprocess(self):
        original = inputs.local_file

        def changed(relative):
            if relative == LEGACY_FIXTURE:
                return Mock(read_bytes=lambda: original(relative).read_bytes() + b"\n")
            return original(relative)

        with patch.object(inputs, "local_file", side_effect=changed):
            with self.assertRaisesRegex(HarnessError, "fingerprint changed"):
                load_plan()

    def test_missing_reordered_or_duplicated_migration_is_refused(self):
        original = inputs.local_file
        manifest_path = f"{inputs.PACKAGE}/manifest.json"
        manifest = json.loads(original(manifest_path).read_text(encoding="utf-8"))
        for mutation in ("missing", "reordered", "duplicate"):
            candidate = deepcopy(manifest)
            paths = list(candidate["migrations"])
            if mutation == "missing":
                candidate["migrations"].pop(paths[0])
            elif mutation == "reordered":
                candidate["migrations"] = dict(reversed(candidate["migrations"].items()))
            else:
                candidate["migrations"]["supabase/migrations/00000000000000_duplicate.sql"] = candidate["migrations"][paths[0]]
            with self.subTest(mutation=mutation):
                def replacement(relative):
                    if relative == manifest_path:
                        return Mock(read_text=lambda **_: json.dumps(candidate))
                    return original(relative)
                with patch.object(inputs, "local_file", side_effect=replacement):
                    with self.assertRaises(HarnessError):
                        load_plan()

    def test_unsafe_paths_are_rejected_before_filesystem_access(self):
        for relative in ("../secret", "/etc/passwd", "//host/share", "C:/secret", "a/./b", "a//b"):
            with self.subTest(relative=relative), patch.object(Path, "lstat") as metadata:
                with self.assertRaises(HarnessError):
                    inputs.local_file(relative)
                metadata.assert_not_called()

    def test_psql_reconnect_include_shell_and_copy_program_are_prohibited(self):
        for sql in ("\\connect hosted", "  \\i /secret", "\\! command", "COPY x FROM PROGRAM 'cmd';"):
            with self.subTest(sql=sql), self.assertRaises(HarnessError):
                safe_sql(sql)

    def test_four_academic_generated_files_match_their_maintained_sources(self):
        load_plan()
        for feature in ("decommission", "foundations", "structure", "sections"):
            with self.subTest(feature=feature):
                generator = inputs.ROOT / f"scripts/maintenance/migrations/build_academic_{feature}.py"
                namespace = runpy.run_path(str(generator))
                destination, expected = namespace["render"]()
                self.assertEqual(destination.read_text(encoding="utf-8"), expected)
