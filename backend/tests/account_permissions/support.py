"""Shared authorization principals and test doubles."""

import asyncio

from types import SimpleNamespace

from unittest.mock import AsyncMock, MagicMock, patch

from uuid import UUID

import pytest

from fastapi.testclient import TestClient

from fastapi.routing import iter_route_contexts

from app.api.platform import institutions

from app.api.platform import organizations

from app.api.admin.dependencies import _ADMIN_ROUTE_PERMISSIONS

from app.api.admin.admin import router as admin_router

from app.api.platform.dependencies import _PLATFORM_ROUTE_PERMISSIONS

from app.api.platform.platform import router as platform_router

from app.core.errors import AppError

from app.core.permissions import DELEGABLE_STAFF_PERMISSIONS

from app.core.security import get_current_user

from app.db import supabase

from app.services.auth import phase81_rbac

from app.main import app

client = TestClient(app, raise_server_exceptions=False)

TENANT_A = "30000000-0000-0000-0000-000000000001"

TENANT_B = "30000000-0000-0000-0000-000000000002"

ACTOR = "10000000-0000-0000-0000-000000000001"

TARGET = "10000000-0000-0000-0000-000000000002"


def _resolved_user(
    role: str, permission_codes: list[str], institution_id: str = TENANT_A
) -> dict:
    return {
        "user_id": ACTOR,
        "auth_user_id": "auth-actor",
        "email": "actor@example.test",
        "roles": [role],
        "status": "active",
        "institution_id": institution_id,
        "role_assignments": [
            {
                "role": role,
                "scope_type": "institution",
                "scope_id": institution_id,
                "scope_organization_id": None,
                "is_active": True,
                "permissions": permission_codes,
            }
        ],
        "permissions_resolved": True,
        "scoped_permissions_resolved": True,
        "effective_permissions": permission_codes,
    }
