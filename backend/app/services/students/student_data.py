"""Student account identity resolved from the authenticated public user."""

from app.core.errors import AppError
from app.core.security import assert_tenant_object
from app.db.supabase import get_admin_client
from app.repositories.admin import admin_academics as identity_repository
from app.repositories.platform import tenancy
from app.schemas.students.student_profile import StudentProfile


def get_own_student(user_id, client=None):
    student = identity_repository.get_student_by_user_id(
        client or get_admin_client(), str(user_id)
    )
    if student is None:
        raise AppError(
            "No student profile is linked to this account",
            404,
            "STUDENT_PROFILE_NOT_FOUND",
        )
    return student


def get_own_profile(user_id, client=None, *, current_user):
    db = client or get_admin_client()
    student = get_own_student(user_id, client=db)
    assert_tenant_object(current_user, student["institution_id"])
    institution = tenancy.get_institution_by_id(db, student["institution_id"]) or {}
    return StudentProfile(
        student_number=student.get("student_number"),
        register_number=student.get("register_number"),
        university_roll_number=student.get("university_roll_number"),
        email=student.get("email"),
        institution_name=institution.get("name"),
        institution_code=institution.get("code"),
        status=student.get("status"),
        approval_status=student.get("approval_status"),
    )
