"""Safe Phase 7.23 contracts for institution Staff/Faculty management."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

MembershipRole = Literal["staff", "faculty"]
MembershipRequestStatus = Literal["pending", "approved", "rejected"]


class MembershipRequestView(BaseModel):
    request_id: UUID
    full_name: str
    email: str
    requested_role: MembershipRole
    status: MembershipRequestStatus
    created_at: datetime | str


class MembershipRequestList(BaseModel):
    requests: list[MembershipRequestView]
    total: int


class MembershipDecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str | None = None


class MembershipDecisionResult(BaseModel):
    request_id: UUID
    status: Literal["approved", "rejected"]
    already_applied: bool = False
    invitation_status: Literal["invited"] | None = None
    message: str


class MembershipRosterEntry(BaseModel):
    user_id: UUID | None = None
    invitation_id: UUID | None = None
    name: str
    email: str
    role: MembershipRole
    status: str
    invitation_status: str | None = None
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None


class MembershipRoster(BaseModel):
    members: list[MembershipRosterEntry]
    total: int


class MembershipLifecycleResult(BaseModel):
    user_id: UUID
    status: Literal["active", "deactivated"]
    already_applied: bool
    message: str

