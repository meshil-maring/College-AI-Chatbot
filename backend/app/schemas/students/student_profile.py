"""Student account profile without internal identifiers or academic records."""

from pydantic import BaseModel, ConfigDict


class StudentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_number: str | None = None
    register_number: str | None = None
    university_roll_number: str | None = None
    email: str | None = None
    institution_name: str | None = None
    institution_code: str | None = None
    status: str | None = None
    approval_status: str | None = None
