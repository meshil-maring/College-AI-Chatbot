from datetime import date
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AttendanceStatus = Literal['present', 'absent', 'late', 'excused']


class RosterStudentInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    register_number: str = Field(min_length=1, max_length=128)
    university_roll_number: str | None = None
    student_name: str = Field(min_length=1, max_length=256)
    email: str | None = None
    address: str | None = None

    @field_validator('register_number', 'student_name', mode='before')
    @classmethod
    def non_blank(cls, value: Any) -> str:
        value = str(value or '').strip()
        if not value:
            raise ValueError('required field is blank')
        return value


class ManualAttendanceRequest(BaseModel):
    session_date: date
    attendance: dict[UUID, AttendanceStatus] = Field(min_length=1)
    notes: str | None = None


class RosterUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    student_name: str | None = None
    email: str | None = None
    address: str | None = None
    roster_status: Literal['UNREGISTERED', 'PENDING_APPROVAL', 'ACTIVE', 'INACTIVE'] | None = None

    @field_validator('student_name', mode='before')
    @classmethod
    def non_blank_name(cls, value: Any) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            raise ValueError('student_name cannot be blank')
        return value


class ImportConfirmRequest(BaseModel):
    ai_confirmed: bool = False


class ImportReview(BaseModel):
    import_id: UUID
    status: str
    summary: dict[str, int]
    rows: list[dict]
