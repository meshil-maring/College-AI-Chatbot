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
    # Required when approving a pending request: the administrator, not the
    # applicant, decides which department the new member belongs to.
    department_id: UUID | None = None
    # Optional: approve the applicant as Staff or Faculty instead of the role
    # they asked for. Administrator and platform roles are not accepted.
    role: MembershipRole | None = None


class MemberRoleWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: MembershipRole


class MemberRoleResult(BaseModel):
    user_id: UUID
    role: MembershipRole
    already_applied: bool
    message: str


class MemberDepartmentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    department_id: UUID


class MemberDepartmentResult(BaseModel):
    user_id: UUID
    department_id: UUID
    department_code: str
    department_name: str
    message: str


class MembershipDecisionResult(BaseModel):
    request_id: UUID
    status: Literal["approved", "rejected"]
    already_applied: bool = False
    message: str


class MembershipRosterEntry(BaseModel):
    user_id: UUID
    name: str
    email: str
    role: MembershipRole
    status: str
    created_at: datetime | str | None = None
    updated_at: datetime | str | None = None
    department_id: UUID | None = None
    department_code: str | None = None
    department_name: str | None = None


class MembershipRoster(BaseModel):
    members: list[MembershipRosterEntry]
    total: int


class MembershipLifecycleResult(BaseModel):
    user_id: UUID
    status: Literal["active", "deactivated"]
    already_applied: bool
    message: str
