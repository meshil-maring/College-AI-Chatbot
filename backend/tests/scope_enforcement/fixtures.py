"""Fixtures."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .database import (
    _db,
)

from .support import (
    INST_A,
    INST_B,
    ORG_A,
    ORG_B,
)


@pytest.fixture(autouse=True)
def _active_institution_authorization():
    """Supply an ACTIVE institution to the scoped admin dependency only.

    Phase 7.20's ``require_institution_roles`` resolves the caller's institution
    from the server-owned ``user_roles`` grant and verifies its lifecycle through
    the authorization module's service-role client. This fixture swaps ONLY that
    client so endpoint tests exercise the real guard. The tenancy repository is
    deliberately left untouched so the lifecycle tests (inactive/pending/rejected
    institutions) and the public-AI pipeline keep resolving real rows.
    """
    active_state = {
        "institutions": {
            INST_A: {
                "institution_id": INST_A,
                "organization_id": ORG_A,
                "status": "active",
                "is_active": True,
            },
            INST_B: {
                "institution_id": INST_B,
                "organization_id": ORG_B,
                "status": "active",
                "is_active": True,
            },
        }
    }
    with patch(
        "app.services.auth.authorization.get_admin_client",
        return_value=_db(active_state),
    ):
        yield
