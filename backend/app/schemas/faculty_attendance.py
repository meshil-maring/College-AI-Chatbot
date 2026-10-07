from datetime import date
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

AttendanceStatus = Literal['present', 'absent', 'late', 'excused']


class RosterStudentInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    register_number: str = Field(min_length=1, max_length=128)
    university_roll_number: str | None = Field(default=None, max_length=128)
    student_name: str = Field(min_length=1, max_length=256)
    email: str | None = Field(default=None, max_length=128)
    address: str | None = Field(default=None, max_length=2000)

    @field_validator('register_number', 'student_name', mode='before')
    @classmethod
    def non_blank(cls, value: Any) -> str:
        value = str(value or '').strip()
        if not value:
            raise ValueError('required field is blank')
        return value


class ManualAttendanceRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    session_date: date
    attendance: dict[UUID, AttendanceStatus] = Field(min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=2000)


class RosterUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    student_name: str | None = Field(default=None, max_length=256)
    email: str | None = Field(default=None, max_length=128)
    address: str | None = Field(default=None, max_length=2000)
    roster_status: Literal['UNREGISTERED', 'PENDING_APPROVAL', 'ACTIVE', 'INACTIVE'] | None = None

    @field_validator('student_name', mode='before')
    @classmethod
    def non_blank_name(cls, value: Any) -> str | None:
        if value is None:
            raise ValueError('student_name cannot be null')
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


class ImportRowCorrection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    data: dict[str, str] = Field(max_length=20)
