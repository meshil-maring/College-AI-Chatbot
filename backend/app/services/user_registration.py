"""Phase 6.13.5 - Student, Faculty & Staff registration service.

Unified registration endpoint for students, faculty, and staff.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories import admin_academics as academics_repo
from app.repositories import tenancy as tenancy_repo
from app.schemas.users import UserRegistrationRequest, UserRegistrationResponse
from app.services import student_registration as student_svc
from app.services import tenancy as tenancy_svc

ROLE_MAP = {"student": "student", "faculty": "faculty", "staff": "staff"}


def _require_student_identifier(register_number, university_roll_number):
    if not register_number and not university_roll_number:
        raise AppError("Provide at least one of register_number or university_roll_number", status_code=422, code="IDENTIFIER_REQUIRED")


def _resolve_institution(db, code: str) -> dict:
    institution = tenancy_repo.get_institution_by_code(db, code)
    if institution is None:
        raise AppError("Institution not found", status_code=404, code="INSTITUTION_NOT_FOUND")
    tenancy_svc._assert_institution_active(institution)
    return institution


def register_user(payload):
    reg_type = payload.registration_type
    code = payload.institution_code.strip().upper()
    email = str(payload.email).strip().lower()
    db = get_admin_client()

    institution = _resolve_institution(db, code)

    existing_user = student_svc._find_user_by_email(db, email)
    if existing_user is not None:
        if reg_type == "student":
            existing_student = academics_repo.get_student_by_user_id(db, existing_user["user_id"])
            if existing_student is not None:
                raise AppError("This account is already registered as a student", status_code=409, code="STUDENT_ALREADY_REGISTERED")
        raise AppError("An account already exists for this email", status_code=409, code="EMAIL_ALREADY_REGISTERED")

    if reg_type == "student":
        register_number = student_svc._normalize_identifier(payload.register_number)
        university_roll_number = student_svc._normalize_identifier(payload.university_roll_number)
        _require_student_identifier(register_number, university_roll_number)
        student_number = student_svc._derive_student_number(register_number, university_roll_number)
        student_svc._assert_no_duplicate_identities(db, institution["institution_id"], email, register_number, university_roll_number)
    else:
        if payload.register_number is not None or payload.university_roll_number is not None:
            raise AppError("Student academic identifiers are only valid for student registration", status_code=422, code="VALIDATION_ERROR")
        register_number = None
        university_roll_number = None
        student_number = None

    auth_user_id = student_svc._create_auth_account(email, payload.password)
    user_id = None
    try:
        user_id = student_svc._create_public_user(db, auth_user_id, email, payload.first_name, payload.last_name)
    except Exception as exc:
        if isinstance(exc, AppError):
            raise
        student_svc._try_delete_auth_user(auth_user_id)
        raise AppError("Registration failed - could not create the account record", status_code=500, code="REGISTRATION_FAILED") from exc

    try:
        if reg_type == "student":
            enrollment_date = date.today()
            student_payload = {
                "user_id": user_id,
                "institution_id": str(institution["institution_id"]),
                "student_number": student_number,
                "email": email,
                "register_number": register_number,
                "university_roll_number": university_roll_number,
                "approval_status": tenancy_svc.PENDING,
                "enrollment_date": enrollment_date.isoformat(),
                "status": "active",
                "is_active": True,
            }
            response = db.table("students").insert(student_payload).execute()
            rows = response.data if isinstance(response.data, list) else [response.data]
            if not rows or not rows[0].get("student_id"):
                raise RuntimeError("students insert did not return a student_id")
            created = rows[0]
            return UserRegistrationResponse(
                message="Student registration submitted. Your account is pending approval by the institution admin.",
                user_id=UUID(str(user_id)),
                institution_id=UUID(str(institution["institution_id"])),
                institution_code=institution["code"],
                registration_type=reg_type,
                approval_status=tenancy_svc.PENDING,
                student_id=UUID(str(created["student_id"])),
                request_id=None,
            )
        else:
            full_name = payload.first_name.strip() + " " + payload.last_name.strip()
            request_row = tenancy_repo.insert_membership_request(
                db,
                institution_id=str(institution["institution_id"]),
                organization_id=str(institution["organization_id"]),
                user_id=str(user_id),
                requested_role=reg_type,
                official_email=email,
                full_name=full_name,
                designation=payload.designation,
                department=payload.department,
            )
            message = reg_type.capitalize() + " registration submitted. Your account is pending approval by the institution admin."
            return UserRegistrationResponse(
                message=message,
                user_id=UUID(str(user_id)),
                institution_id=UUID(str(institution["institution_id"])),
                institution_code=institution["code"],
                registration_type=reg_type,
                approval_status=tenancy_svc.PENDING,
                student_id=None,
                request_id=UUID(str(request_row["request_id"])),
            )
    except Exception as exc:
        if user_id is not None:
            student_svc._try_delete_user_row(db, user_id)
        student_svc._try_delete_auth_user(auth_user_id)
        if isinstance(exc, AppError):
            raise
        raise AppError("Registration failed - could not complete registration", status_code=500, code="REGISTRATION_FAILED") from exc