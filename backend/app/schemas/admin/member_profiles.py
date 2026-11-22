"""Contracts for Staff/Faculty employee profiles (User Management U1, U3, U4).

The administrator enters a common profile shared by every member type and the
profile of the member's role. Field rules mirror the database CHECK constraints
in 20261128000000_member_profiles so invalid input fails with a clear 422
before any write. The database repeats every rule.
"""

import re
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.admin.admin_memberships import MembershipRole

FacultyEmploymentType = Literal["permanent", "temporary", "contractual", "visiting", "guest"]
StaffEmploymentType = Literal["permanent", "temporary", "contractual"]
StaffCategory = Literal[
    "office_administration", "accounts_finance", "library", "it_support",
    "laboratory", "hostel_administration", "examination_office", "other",
]
EmploymentStatus = Literal["active", "contract_ended", "not_set"]

_EMPLOYEE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,39}$")
_PHONE = re.compile(r"^\+?[0-9][0-9 ()-]{4,30}$")


def _text(value: str | None) -> str | None:
    """Collapse whitespace; blank optional text becomes None."""
    if value is None:
        return None
    trimmed = " ".join(value.split())
    return trimmed or None


class CommonProfile(BaseModel):
    """Fields shared by Admin, Faculty and Staff."""

    model_config = ConfigDict(extra="forbid")

    employee_id: str = Field(min_length=1, max_length=40)
    phone: str | None = Field(default=None, max_length=32)
    designation: str = Field(min_length=1, max_length=120)
    joining_date: date

    @field_validator("employee_id")
    @classmethod
    def _employee_id(cls, value: str) -> str:
        value = value.strip()
        if not _EMPLOYEE_ID.match(value):
            raise ValueError("Use letters, numbers and . _ / - for the employee ID")
        return value

    @field_validator("phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        value = _text(value)
        if value is not None and not _PHONE.match(value):
            raise ValueError("Enter a valid phone number")
        return value

    @field_validator("designation")
    @classmethod
    def _designation(cls, value: str) -> str:
        value = _text(value)
        if not value:
            raise ValueError("Enter the designation")
        return value


class _Employment(BaseModel):
    """Contract end date is required unless employment is permanent.

    Subclasses define ``employment_type`` with the types allowed for the role.
    """

    model_config = ConfigDict(extra="forbid")

    employment_type: str
    employment_start_date: date
    contract_end_date: date | None = None

    @model_validator(mode="after")
    def _contract(self):
        if self.employment_type != "permanent" and self.contract_end_date is None:
            raise ValueError("Enter the contract end date for non-permanent employment")
        if self.contract_end_date is not None and self.contract_end_date < self.employment_start_date:
            raise ValueError("The contract cannot end before employment starts")
        return self


class FacultyProfile(_Employment):
    qualification: str | None = Field(default=None, max_length=200)
    specialization: str | None = Field(default=None, max_length=200)
    experience_years: float | None = Field(default=None, ge=0, le=70)
    employment_type: FacultyEmploymentType

    @field_validator("qualification", "specialization")
    @classmethod
    def _optional_text(cls, value: str | None) -> str | None:
        return _text(value)

    @field_validator("experience_years")
    @classmethod
    def _one_decimal(cls, value: float | None) -> float | None:
        return None if value is None else round(value, 1)


class StaffProfile(_Employment):
    staff_category: StaffCategory
    employment_type: StaffEmploymentType
    responsibilities: list[str] = Field(min_length=1, max_length=20)

    @field_validator("responsibilities")
    @classmethod
    def _responsibilities(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            text = _text(value)
            if not text or len(text) > 80:
                raise ValueError("Each responsibility must be 1 to 80 characters")
            if text.lower() not in {item.lower() for item in cleaned}:
                cleaned.append(text)
        return cleaned


class MemberProfileWrite(BaseModel):
    """The common profile plus exactly one role profile."""

    model_config = ConfigDict(extra="forbid")

    common: CommonProfile
    faculty: FacultyProfile | None = None
    staff: StaffProfile | None = None

    @model_validator(mode="after")
    def _one_role(self):
        if (self.faculty is None) == (self.staff is None):
            raise ValueError("Provide either the faculty or the staff details")
        return self

    @property
    def role(self) -> MembershipRole:
        return "faculty" if self.faculty is not None else "staff"

    def database_payload(self) -> dict:
        """JSON stored by the database commands: common plus the role section."""
        return self.model_dump(mode="json", exclude_none=True)


class DepartmentRef(BaseModel):
    department_id: UUID
    code: str
    name: str


class MemberProfileView(BaseModel):
    user_id: UUID
    role: MembershipRole
    common: CommonProfile | None = None
    faculty: FacultyProfile | None = None
    staff: StaffProfile | None = None
    employment_status: EmploymentStatus
    primary_department: DepartmentRef | None = None
    additional_departments: list[DepartmentRef] = Field(default_factory=list)


class MemberProfileSaved(BaseModel):
    user_id: UUID
    role: MembershipRole
    message: str


class MemberAdditionalDepartmentsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    department_ids: list[UUID] = Field(default_factory=list, max_length=10)


class MemberAdditionalDepartmentsResult(BaseModel):
    user_id: UUID
    additional_departments: list[DepartmentRef]
    message: str


class MemberHistoryEntry(BaseModel):
    audit_id: UUID
    action: str
    label: str
    actor_name: str
    performed_at: datetime | str
    details: dict = Field(default_factory=dict)


class MemberHistory(BaseModel):
    user_id: UUID
    entries: list[MemberHistoryEntry]
