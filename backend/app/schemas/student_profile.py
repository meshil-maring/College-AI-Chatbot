"""Phase 6.14.1 — Student academic profile response contract.

Student-facing, reusable representation of the authenticated student's
academic profile. Derived server-side only (never from client-supplied
identifiers) via ``app.services.student_academic_profile``.

Deliberately exposes NO internal database identifiers (no ``student_id``,
``user_id``, ``auth_user_id``, ``institution_id``, ``program_id``,
``academic_year_id``). The endpoint accepts no identity parameters, so
client-supplied identifiers cannot override the authenticated identity.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StudentAcademicProfile(BaseModel):
    """Student-facing academic profile (no internal database identifiers)."""

    student_number: str | None = None
    register_number: str | None = None
    university_roll_number: str | None = None
    email: str | None = None
    institution_name: str | None = None
    institution_code: str | None = None
    program_name: str | None = None
    program_code: str | None = None
    academic_year_name: str | None = None
    academic_year_code: str | None = None
    current_semester_name: str | None = None
    current_semester_code: str | None = None
    approval_status: str | None = None
    status: str | None = None

    model_config = ConfigDict(extra="forbid")
