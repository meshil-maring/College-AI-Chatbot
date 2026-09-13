"""Phase 6.3 — Student self-service registration.

A prospective student submits a registration request for a specific
institution. The registration flow:

    registration payload
      -> validate institution (exists, is_active = accepting registrations)
      -> validate institution-scoped identity fields (email, register
         number, university roll number)
      -> create the Supabase Auth account through the EXISTING auth
         mechanism (never a second auth architecture, never a stored
         password - the password goes only to Supabase Auth GoTrue)
      -> create the public.users link row (auth user -> public user)
      -> create the students profile with approval_status = 'pending'
      -> registration response (clearly pending approval)

Architecture preserved exactly as locked in earlier phases::

    auth.users (Supabase GoTrue)
         |  users.auth_user_id
    public.users
         |  students.user_id
    students
         |  students.institution_id
    institutions

Approval is exclusively Phase 6.4. This flow NEVER produces ``approved``,
never assigns roles, never accepts client role / approval-status /
institution-creation fields, and never grants approved-student access. No
role is granted at registration time either - role/approval is the
Phase 6.4 admin workflow's decision.

Failure handling: Supabase Auth operations (GoTrue) cannot participate in
the PostgREST transaction that inserts public.users / students rows, so
partial failures are compensated explicitly, documented below:

* Auth account created, then public.users insert fails
  -> the auth account is deleted via the service-role admin API
     (``auth.admin.delete_user``) - best-effort compensation.
* Auth account + public.users created, then students insert fails
  -> the public.users row is deleted (service-role delete) and the auth
     account is deleted - best-effort.

Because the compensation calls are best-effort (a GoTrue/PostgREST
operation), a crash between steps can in rare cases leave an auth account
without a public profile; the Phase 6.4 approval queue runs on ``students``
rows and could safely request re-registration. No identity values are
duplicated anywhere.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from supabase_auth.errors import AuthApiError

from app.core.errors import AppError
from app.db.supabase import create_supabase_client, get_admin_client
from app.repositories import admin_academics as academics_repo

# Approval lifecycle value every registered student must start with. Phase 6.4
# owns the transition pending -> approved | rejected.
PENDING = "pending"

INSTITUTION_COLUMNS = "institution_id, name, code, is_active"


def _normalize_identifier(value: str | None) -> str | None:
    """Trim an optional identifier; empty / whitespace-only becomes None."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _derive_student_number(
    register_number: str | None,
    university_roll_number: str | None,
) -> str:
    """Derive the required students.student_number from the submitted identity.

    ``students.student_number`` is NOT NULL (Admin-1) with a non-blank CHECK
    and an institution-scoped UNIQUE key (Phase 6.2), and it is the
    institution-assigned academic number used by CSV result upload and the
    admin student list ordering. Registration deliberately does NOT ask the
    client for a separate ``student_number`` value ("do not duplicate
    student_number unnecessarily"): the register number (or the university
    roll number) already is the student's assigned number, so it becomes the
    stored ``student_number``. Because self-registration requires at least
    one of those identifiers (validated below), the server never needs to
    fabricate a synthetic placeholder.
    """
    if register_number:
        return register_number
    # university_roll_number is guaranteed non-None here by require_identifier.
    return university_roll_number  # type: ignore[return-value]


def _require_identifier(
    register_number: str | None,
    university_roll_number: str | None,
) -> None:
    """Self-registration must carry at least one academic identifier.

    Rationale: ``student_number`` is an institution-assigned academic
    identifier (NOT NULL, non-blank, unique per institution). Allowing a
    registration with neither register number nor university roll number
    would force the backend to invent a synthetic ``student_number``
    (e.g. a constant placeholder colliding under the UNIQUE key, or a
    random token that looks like a real academic number to CSV upload,
    admin listings, and Phase 6.4 approval). Requiring one real identifier
    keeps every stored ``student_number`` a genuine institution value while
    asking for no extra ``student_number`` field (per the brief). Email alone
    is a login identity, not an academic number, so it cannot substitute.
    """
    if register_number or university_roll_number:
        return
    raise AppError(
        "Provide at least one of register_number or university_roll_number",
        status_code=422,
        code="IDENTIFIER_REQUIRED",
    )


class StudentRegistrationRequest(BaseModel):
    """Public self-service registration payload, institution-keyed.

    ``extra="forbid"`` is deliberate: the endpoint must NEVER accept
    arbitrary client fields such as ``role`` / ``approval_status`` /
    institution-creation keys. Only the fields below may be submitted.
    """

    model_config = ConfigDict(extra="forbid")

    institution_id: UUID
    email: EmailStr
    password: str  # goes ONLY to Supabase Auth (never stored in this DB)
    first_name: str
    last_name: str
    register_number: str | None = None
    university_roll_number: str | None = None
    enrollment_date: date | None = None

    @field_validator("password")
    @classmethod
    def _password_minimum_length(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

    @field_validator("first_name", "last_name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @field_validator("register_number", "university_roll_number")
    @classmethod
    def _identity_blank_to_none(cls, v: str | None) -> str | None:
        return _normalize_identifier(v)


class RegistrationResponse(BaseModel):
    """Response returned to a successful registration submission.

    Clearly states pending approval and never exposes a password, auth
    token, role assignments, or another student's information.
    """

    message: str
    student_id: UUID
    institution_id: UUID
    email: EmailStr
    approval_status: str = PENDING


# ============================================================================
# Validation helpers
# ============================================================================


def _get_institution(db, institution_id: UUID | str) -> dict:
    """Return the institution row, validating existence + registration eligibility.

    The client can never create an institution here (no institutions write
    ever happens); it can only reference an existing, active institution.
    """
    response = (
        db.table("institutions")
        .select(INSTITUTION_COLUMNS)
        .eq("institution_id", str(institution_id))
        .maybe_single()
        .execute()
    )
    institution = response.data
    if institution is None:
        raise AppError(
            "Institution not found",
            status_code=404,
            code="INSTITUTION_NOT_FOUND",
        )
    if not institution.get("is_active", True):
        raise AppError(
            "This institution is not currently accepting student registrations",
            status_code=403,
            code="INSTITUTION_NOT_ACCEPTING_REGISTRATIONS",
        )
    return institution


def _find_user_by_email(db, email: str) -> dict | None:
    """Resolve an existing public.users row by account email (globally unique)."""
    response = (
        db.table("users")
        .select("user_id, email")
        .eq("email", email)
        .maybe_single()
        .execute()
    )
    return response.data


def _assert_no_duplicate_identities(
    db,
    institution_id: UUID | str,
    email: str,
    register_number: str | None,
    university_roll_number: str | None,
) -> None:
    """Reject identity values already used by another student IN THIS INSTITUTION.

    Uniqueness is institution-scoped (Phase 6.2): the same register number at
    a different institution is never considered a duplicate here.
    """
    if (
        academics_repo.get_student_by_email(db, institution_id, email) is not None
    ):
        raise AppError(
            "This email is already registered as a student at this institution",
            status_code=409,
            code="EMAIL_ALREADY_REGISTERED",
        )
    if register_number is not None and (
        academics_repo.get_student_by_register_number(
            db, institution_id, register_number
        )
        is not None
    ):
        raise AppError(
            "This register number is already registered at this institution",
            status_code=409,
            code="REGISTER_NUMBER_ALREADY_REGISTERED",
        )
    if university_roll_number is not None and (
        academics_repo.get_student_by_university_roll_number(
            db, institution_id, university_roll_number
        )
        is not None
    ):
        raise AppError(
            "This university roll number is already registered at this institution",
            status_code=409,
            code="ROLL_NUMBER_ALREADY_REGISTERED",
        )
def _create_auth_account(email: str, password: str) -> str:
    """Create the Supabase Auth account via the existing signup mechanism.

    The password is handed to GoTrue and is never stored, hashed, or logged
    by this application. Duplicate auth emails surface as AuthApiError and
    are translated to the project's AppError convention.
    """
    client = create_supabase_client()
    try:
        response = client.auth.sign_up({"email": email, "password": password})
    except AuthApiError as exc:
        # Supabase reports an already-registered auth email with 4xx
        # (typically 422 email_exists / 400 user_already_exists). That is a
        # duplicate-registration conflict, not an internal failure.
        status = exc.status or 400
        message = str(getattr(exc, "message", "") or "").lower()
        if status in (400, 409, 422) and (
            "already" in message or "exists" in message or "duplicate" in message
        ):
            raise AppError(
                "An account already exists for this email",
                status_code=409,
                code="EMAIL_ALREADY_REGISTERED",
            ) from exc
        raise AppError(
            str(getattr(exc, "message", "") or "Authentication failed"),
            status_code=status,
            code="AUTH_ERROR",
        ) from exc
    return response.user.id


def _create_public_user(
    db,
    auth_user_id: str,
    email: str,
    first_name: str,
    last_name: str,
) -> str:
    """Insert the public.users link row; returns the generated user_id."""
    response = (
        db.table("users")
        .insert(
            {
                "auth_user_id": auth_user_id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "display_name": f"{first_name} {last_name}".strip() or None,
                "status": "active",
            }
        )
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else [response.data]
    if not rows or not rows[0].get("user_id"):
        raise RuntimeError("public.users insert did not return a user_id")
    return rows[0]["user_id"]


def _create_student_profile(
    db,
    *,
    user_id: str,
    institution_id: UUID | str,
    student_number: str,
    email: str,
    register_number: str | None,
    university_roll_number: str | None,
    enrollment_date: date,
) -> dict:
    """Insert the students profile explicitly as pending; returns the row."""
    payload = {
        "user_id": user_id,
        "institution_id": str(institution_id),
        "student_number": student_number,
        "email": email,
        "register_number": register_number,
        "university_roll_number": university_roll_number,
        "approval_status": PENDING,
        "enrollment_date": enrollment_date.isoformat(),
        "status": "active",
        "is_active": True,
    }
    response = db.table("students").insert(payload).execute()
    rows = response.data if isinstance(response.data, list) else [response.data]
    if not rows or not rows[0].get("student_id"):
        raise RuntimeError("students insert did not return a student_id")
    return rows[0]


def _try_delete_auth_user(auth_user_id: str) -> None:
    """Best-effort compensation: remove a freshly created Supabase auth account.

    GoTrue is outside the PostgREST transaction; failures here are swallowed
    so the primary AppError is not masked.
    """
    try:
        get_admin_client().auth.admin.delete_user(auth_user_id)
    except Exception:  # noqa: BLE001 - compensation must never mask the error
        pass


def _try_delete_user_row(db, user_id: str) -> None:
    """Best-effort compensation: remove a freshly created public.users row."""
    try:
        db.table("users").delete().eq("user_id", user_id).execute()
    except Exception:  # noqa: BLE001 - compensation must never mask the error
        pass


# ============================================================================
# Registration orchestration
# ============================================================================


def register_student(payload: StudentRegistrationRequest) -> RegistrationResponse:
    """Register a prospective student for a specific institution (pending).

    Never produces ``approved``, never assigns roles, and never lets a
    client value influence privileges: only the fields defined on
    ``StudentRegistrationRequest`` (all others rejected with 422) are read.
    """
    email = str(payload.email).strip().lower()
    register_number = _normalize_identifier(payload.register_number)
    university_roll_number = _normalize_identifier(payload.university_roll_number)
    # Fail fast on missing academic identity, before touching Supabase Auth
    # or any table: no synthetic student_number is ever fabricated.
    _require_identifier(register_number, university_roll_number)
    student_number = _derive_student_number(register_number, university_roll_number)
    enrollment_date = payload.enrollment_date or date.today()
    first_name = str(payload.first_name).strip()
    last_name = str(payload.last_name).strip()

    db = get_admin_client()

    # 1. Institution must exist and be accepting registrations. No write to
    #    institutions can ever happen from this flow.
    _get_institution(db, payload.institution_id)

    # 2. Existing account handling: never duplicate auth/public users. One
    #    email = one account globally (public.users.email + Supabase Auth).
    existing_user = _find_user_by_email(db, email)
    if existing_user is not None:
        existing_student = academics_repo.get_student_by_user_id(
            db, existing_user["user_id"]
        )
        if existing_student is not None:
            raise AppError(
                "This account is already registered as a student",
                status_code=409,
                code="STUDENT_ALREADY_REGISTERED",
            )
        raise AppError(
            "An account already exists for this email",
            status_code=409,
            code="EMAIL_ALREADY_REGISTERED",
        )

    # 3. Identity duplicates are institution-scoped (Phase 6.2): identical
    #    register/roll values at another institution are never a conflict.
    _assert_no_duplicate_identities(
        db,
        payload.institution_id,
        email,
        register_number,
        university_roll_number,
    )

    # 4. Create the Supabase Auth account through the existing mechanism.
    auth_user_id = _create_auth_account(email, payload.password)

    # 5. Create the public.users link row; compensate on failure.
    user_id: str | None = None
    try:
        user_id = _create_public_user(
            db,
            auth_user_id,
            email,
            first_name,
            last_name,
        )
    except AppError:
        raise
    except Exception as exc:
        _try_delete_auth_user(auth_user_id)
        raise AppError(
            "Registration failed - could not create the account record",
            status_code=500,
            code="REGISTRATION_FAILED",
        ) from exc

    # 6. Create the students profile - always pending; compensate on failure.
    try:
        created = _create_student_profile(
            db,
            user_id=user_id,
            institution_id=payload.institution_id,
            student_number=student_number,
            email=email,
            register_number=register_number,
            university_roll_number=university_roll_number,
            enrollment_date=enrollment_date,
        )
    except Exception as exc:
        if user_id is not None:
            _try_delete_user_row(db, user_id)
        _try_delete_auth_user(auth_user_id)
        raise AppError(
            "Registration failed - could not create the student profile",
            status_code=500,
            code="REGISTRATION_FAILED",
        ) from exc

    return RegistrationResponse(
        message="Registration submitted. Your account is pending approval.",
        student_id=created["student_id"],
        institution_id=payload.institution_id,
        email=email,
        approval_status=PENDING,
    )