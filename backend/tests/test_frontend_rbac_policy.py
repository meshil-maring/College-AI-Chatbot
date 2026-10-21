"""Prevent frontend bootstrap references from drifting from backend policy."""

from pathlib import Path
import runpy


def test_frontend_rbac_snapshot_matches_the_backend_catalog():
    root = Path(__file__).resolve().parents[2]
    generator = runpy.run_path(str(root / "backend/scripts/generate_frontend_rbac.py"))
    actual = (root / "frontend/src/features/auth/rbacPolicy.generated.ts").read_text(encoding="utf-8")
    assert actual == generator["render_policy"](), "Regenerate the frontend RBAC snapshot after changing backend defaults"
