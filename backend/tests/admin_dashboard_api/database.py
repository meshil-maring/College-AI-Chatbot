"""Dashboard database fixtures."""

from __future__ import annotations
from contextlib import contextmanager
from unittest.mock import MagicMock, patch
from app.core.security import get_current_user
from app.main import app
from .support import ADMIN_A_USER, INST_A


class _RecordingClient:
    """Service-role client double that records every ``.eq()`` tenant filter."""

    def __init__(self):
        self.filters: dict[str, list[tuple]] = {}
        self.tables: list[str] = []
        self.selects: list[tuple[str, tuple]] = []

    def table(self, name):
        self.tables.append(name)
        counts = MagicMock(count=0, data=[])
        m = MagicMock()
        sel = m.select.return_value

        def _select(*args, **kwargs):
            self.selects.append((name, args, kwargs))
            return sel

        m.select.side_effect = _select

        def _eq(*args, **kwargs):
            self.filters.setdefault(name, []).append(args)
            return sel

        sel.eq.side_effect = _eq
        sel.in_.side_effect = lambda *a, **k: sel
        sel.execute.return_value = counts
        sel.eq.return_value.execute.return_value = counts
        sel.eq.return_value.eq.return_value.execute.return_value = counts
        sel.eq.return_value.in_.return_value.execute.return_value = counts
        return m


@contextmanager
def _real_service(db: _RecordingClient | None = None, notices=None):
    """Stub ONLY the data layer so the REAL dashboard service executes.

    ``app.services.auth.authorization`` and ``app.services.admin.admin_dashboard`` both hold
    a reference to the SAME ``app.repositories.platform.tenancy`` module, so a single
    patch covers both: the row must satisfy the authorization lifecycle check
    (``status``/``is_active``) AND carry the display fields the dashboard reads.
    """
    db = db if db is not None else _RecordingClient()
    app.dependency_overrides[get_current_user] = lambda: ADMIN_A_USER
    with (
        patch(
            "app.services.auth.authorization.get_admin_client", return_value=MagicMock()
        ),
        patch(
            "app.repositories.platform.tenancy.get_institution_by_id",
            return_value=_institution_row(),
        ),
        patch("app.services.admin.admin_dashboard.get_admin_client", return_value=db),
        patch(
            "app.services.admin.admin_dashboard.knowledge_repo.list_notices",
            return_value=notices if notices is not None else [],
        ),
    ):
        yield db
    app.dependency_overrides.pop(get_current_user, None)


def _institution_row() -> dict:
    return {
        "institution_id": INST_A,
        "name": "Alpha University",
        "code": "ALPHA",
        "status": "active",
        "is_active": True,
    }
