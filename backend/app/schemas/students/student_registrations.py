from uuid import UUID
from pydantic import EmailStr, Field, field_validator

from app.schemas.faculty.faculty_attendance import RosterStudentInput


class StudentRegistrationCreate(RosterStudentInput):
    batch_id: UUID
    email: EmailStr = Field(max_length=128)
    auto_send_invitation: bool = False

    @field_validator('university_roll_number', 'email', 'address', mode='before')
    @classmethod
    def optional_text(cls, value):
        return str(value).strip() or None if value is not None else None
