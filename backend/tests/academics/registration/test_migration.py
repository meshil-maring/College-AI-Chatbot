import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]


def generator():
    path = ROOT / "scripts/maintenance/migrations/build_semester_registration.py"
    spec = importlib.util.spec_from_file_location("registration_migration_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registration_migration_has_a_unique_version():
    target, _ = generator().render()
    assert list(target.parent.glob(f"{target.name.split('_', 1)[0]}_*.sql")) == [target]


def test_generator_rejects_a_version_owned_by_another_feature(tmp_path, monkeypatch):
    module = generator()
    source = tmp_path / "supabase/migration_sources/semester_registration"
    source.mkdir(parents=True)
    (source / "manifest.json").write_text(json.dumps({
        "version": "20261030000000", "name": "semester_registration", "files": ["tables.sql"],
    }), encoding="utf-8")
    (source / "tables.sql").write_text("SELECT 1;\n", encoding="utf-8")
    migrations = tmp_path / "supabase/migrations"
    migrations.mkdir()
    (migrations / "20261030000000_other_feature.sql").write_text("SELECT 2;\n", encoding="utf-8")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "SOURCE", source)
    with pytest.raises(ValueError, match="already used by"):
        module.render()
