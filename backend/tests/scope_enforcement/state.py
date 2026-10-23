"""State."""

from __future__ import annotations

from uuid import UUID, uuid4

from .support import (
    INST_A,
    INST_ADMIN,
    JR_A,
    MR_A,
    ORG_A,
    ROLE_ID,
)


def _org_row(org_id=ORG_A, status="pending"):
    return {
        "organization_id": org_id,
        "name": "Acme Org",
        "organization_code": "ACME" if org_id == ORG_A else "BETA",
        "official_email": "info@acme.example.com",
        "contact_information": "contact@acme.example.com",
        "status": status,
        "join_code": None,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z",
    }


def _inst_row(inst_id=INST_A, org_id=ORG_A, status="pending", is_active=False):
    return {
        "institution_id": inst_id,
        "organization_id": org_id,
        "name": "Imphal College",
        "code": "IMPHAL" if inst_id == INST_A else "BETACOLLEGE",
        "email": None,
        "address": None,
        "city": None,
        "state": None,
        "country": None,
        "status": status,
        "is_active": is_active,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z",
    }


def _jr_row(join_request_id=JR_A, org_id=ORG_A, inst_id=INST_A, status="pending"):
    return {
        "join_request_id": join_request_id,
        "organization_id": org_id,
        "institution_id": inst_id,
        "requested_institution_code": "IMPHAL",
        "requested_by_user_id": INST_ADMIN,
        "status": status,
        "decision_reason": None,
        "decided_by_user_id": None,
        "decided_at": None,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z",
    }


def _mr_row(request_id=MR_A, inst_id=INST_A, org_id=ORG_A, status="pending"):
    return {
        "request_id": request_id,
        "institution_id": inst_id,
        "organization_id": org_id,
        "user_id": str(uuid4()),
        "requested_role": "staff",
        "official_email": "staff@imphal.example.com",
        "full_name": "Staff Member",
        "designation": None,
        "department": None,
        "status": status,
        "decision_reason": None,
        "decided_by_user_id": None,
        "decided_at": None,
        "created_at": "2026-09-18T00:00:00Z",
        "updated_at": "2026-09-18T00:00:00Z",
    }


def _base_state(org_status="pending", inst_status="pending", inst_active=False):
    return {
        "organizations": {ORG_A: _org_row(status=org_status)},
        "institutions": {INST_A: _inst_row(status=inst_status, is_active=inst_active)},
        "institution_join_requests": {JR_A: _jr_row()},
        "institution_membership_requests": {MR_A: _mr_row()},
        "roles": {ROLE_ID: {"role_id": ROLE_ID, "name": "staff", "is_active": True}},
        "users": [],
        "user_roles": [],
        "updates": [],
    }
