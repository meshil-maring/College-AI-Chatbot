"""Keep the deployable SQL identical to the bounded maintained source."""

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("entity", ["department", "program", "calendar_section"])
def test_deletion_migration_matches_sources(entity):
    generator = ROOT / f"scripts/maintenance/migrations/build_{entity}_deletion.py"
    spec = importlib.util.spec_from_file_location(f"{entity}_deletion_generator", generator)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target, expected = module.render()
    assert target.read_text(encoding="utf-8") == expected
