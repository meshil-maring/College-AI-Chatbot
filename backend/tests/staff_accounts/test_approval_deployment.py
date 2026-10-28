"""An outdated deployed approval contract must fail closed and be actionable."""

from pathlib import Path
import runpy
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.core.errors import AppError
from app.repositories.admin.admin_memberships import approve_and_grant_role


@pytest.mark.parametrize("response", [
    {"already_applied": True},
    {"already_applied": False, "role_granted": True},
])
def test_legacy_database_success_requires_contract_repair(response):
    client = MagicMock()
    client.rpc.return_value.execute.return_value = SimpleNamespace(data=response)
    with pytest.raises(AppError) as failure:
        approve_and_grant_role(
            client, request_id="request", institution_id="institution",
            decided_by_user_id="admin", reason=None,
        )
    assert failure.value.status_code == 503
    assert failure.value.code == "MEMBERSHIP_APPROVAL_UNAVAILABLE"
    assert "retry sign-in setup" in failure.value.message


def test_membership_repair_generated_from_bounded_sources():
    root = Path(__file__).resolve().parents[3]
    builder = root / "scripts/maintenance/migrations/build_membership_approval.py"
    target, expected = runpy.run_path(str(builder))["render"]()
    assert target.read_text(encoding="utf-8") == expected
    source = root / "supabase/migration_sources/membership_approval"
    assert sum(path.is_file() for path in source.iterdir()) <= 15
    assert all(len(path.read_text(encoding="utf-8").splitlines()) <= 250 for path in source.iterdir())
