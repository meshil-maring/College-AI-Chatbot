"""Offline generator safeguards and byte preservation of Stage 1/2 release sources."""
from hashlib import sha256
import json
from pathlib import Path
import runpy

import pytest


ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / "scripts/maintenance/migrations/build_academic_sections.py"


def test_prior_release_sources_generators_and_migrations_keep_exact_bytes():
    fingerprints = json.loads(
        Path(__file__).with_name("prior_release_fingerprints.json").read_text(encoding="utf-8")
    )
    assert len(fingerprints) == 20
    for relative, expected in fingerprints.items():
        assert sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative


def make_builder(tmp_path, files=None):
    source = tmp_path / "migration_sources/academic_sections"
    source.mkdir(parents=True)
    (source / "manifest.json").write_text(json.dumps({
        "version": "20261024010000", "name": "academic_sections", "files": files or ["tables.sql"],
    }))
    (source / "tables.sql").write_text("CREATE TABLE bounded_source (id uuid);\n")
    render = runpy.run_path(str(BUILDER))["render"]
    render.__globals__["SOURCE"] = source
    render.__globals__["ROOT"] = tmp_path
    return render, source


def test_generator_rejects_sources_escaping_feature_directory(tmp_path):
    render, _ = make_builder(tmp_path, ["../outside.sql"])
    with pytest.raises(ValueError, match="must stay in the academic sections feature"):
        render()


def test_generator_rejects_oversized_maintained_source(tmp_path):
    render, source = make_builder(tmp_path)
    (source / "tables.sql").write_text("-- line\n" * 251)
    with pytest.raises(ValueError, match="exceeds 250 lines"):
        render()


def test_generator_rejects_nested_outer_transactions(tmp_path):
    render, source = make_builder(tmp_path)
    (source / "tables.sql").write_text("BEGIN;\nCREATE TABLE bad (id uuid);\nCOMMIT;\n")
    with pytest.raises(ValueError, match="must not contain outer transactions"):
        render()


def test_generator_rejects_duplicate_source_entries(tmp_path):
    render, _ = make_builder(tmp_path, ["tables.sql", "tables.sql"])
    with pytest.raises(ValueError, match="explicit and unique"):
        render()


def test_generator_rejects_folder_exceeding_fifteen_maintained_files(tmp_path):
    render, source = make_builder(tmp_path)
    for number in range(14):
        (source / f"extra_{number}.sql").write_text("-- source\n")
    with pytest.raises(ValueError, match="exceeds 15 files"):
        render()
