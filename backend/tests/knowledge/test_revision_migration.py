"""Offline integrity of the generated knowledge revision migration artifact."""

import json
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / "scripts/maintenance/migrations/build_knowledge_revisions.py"


@pytest.mark.parametrize('builder, source_name', [
    ('build_knowledge_revisions.py', 'knowledge_revisions'), ('build_resource_chat.py', 'resource_chat'),
    ('build_chat_turns.py', 'chat_turns'),
    ('build_history_citations.py', 'history_citations'),
])
def test_generated_migration_matches_bounded_sources(builder, source_name):
    target, expected = runpy.run_path(str(BUILDER.with_name(builder)))["render"]()
    assert target.read_text(encoding="utf-8") == expected
    source = ROOT / 'supabase/migration_sources' / source_name
    assert sum(path.is_file() for path in source.iterdir()) <= 15
    assert all(len(path.read_text(encoding="utf-8").splitlines()) <= 250
               for path in source.iterdir() if path.is_file())


@pytest.mark.parametrize("files", [["../outside.sql"], ["tables.sql", "tables.sql"]])
def test_generator_rejects_unsafe_or_duplicate_source_manifest(tmp_path, files):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "version": "20261028010000", "name": "knowledge_audience_revisions", "files": files,
    }), encoding="utf-8")
    render = runpy.run_path(str(BUILDER))["render"]
    render.__globals__["SOURCE"] = tmp_path
    with pytest.raises(ValueError):
        render()
