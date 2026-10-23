"""Canonical student identity and approval queries shared by account services.

The established import path remains used by registration, login and approval.
Academic records and academic master references have been retired.
"""

from app.repositories.shared.query_pages import read_one, read_rows

STUDENT_IDENTITY_COLUMNS = (
    "student_id,user_id,institution_id,student_number,email,register_number,"
    "university_roll_number,approval_status,status,is_active"
)
STUDENT_APPROVAL_COLUMNS = (
    STUDENT_IDENTITY_COLUMNS + ",enrollment_date,created_at,updated_at"
)
STUDENT_COLUMNS = STUDENT_APPROVAL_COLUMNS


def _single_row(response):
    return None if response is None else response.data


def _identity(client, column, value, institution_id=None):
    query = (
        client.table("students").select(STUDENT_IDENTITY_COLUMNS).eq(column, str(value))
    )
    if institution_id is not None:
        query = query.eq("institution_id", str(institution_id))
    return read_one(query.maybe_single())


def get_student(client, student_id):
    return _identity(client, "student_id", student_id)


def get_student_by_user_id(client, user_id):
    return _identity(client, "user_id", user_id)


def get_student_approval_row_by_user_id(client, user_id):
    return read_one(
        client.table("students")
        .select(STUDENT_APPROVAL_COLUMNS)
        .eq("user_id", str(user_id))
        .maybe_single()
    )


def get_student_by_email(client, institution_id, email):
    return _identity(client, "email", str(email).strip().lower(), institution_id)


def get_student_by_email_global(client, email):
    return _identity(client, "email", str(email).strip().lower())


def get_student_by_register_number(client, institution_id, register_number):
    return _identity(
        client, "register_number", str(register_number).strip(), institution_id
    )


def get_student_by_university_roll_number(
    client, institution_id, university_roll_number
):
    return _identity(
        client,
        "university_roll_number",
        str(university_roll_number).strip(),
        institution_id,
    )


def get_student_by_register_number_global(client, register_number):
    return read_rows(
        client.table("students")
        .select(STUDENT_IDENTITY_COLUMNS)
        .eq("register_number", str(register_number).strip())
    )


def get_student_by_university_roll_number_global(client, university_roll_number):
    return read_rows(
        client.table("students")
        .select(STUDENT_IDENTITY_COLUMNS)
        .eq("university_roll_number", str(university_roll_number).strip())
    )


def resolve_student_by_identifier(client, institution_id, identifier):
    value = str(identifier).strip()
    if not value:
        return None
    for lookup in (
        get_student_by_email,
        get_student_by_register_number,
        get_student_by_university_roll_number,
    ):
        student = lookup(client, institution_id, value)
        if student is not None:
            return student
    return None


def list_pending_students(client, institution_id=None, limit=100, offset=0):
    query = client.table("students").select(STUDENT_APPROVAL_COLUMNS)
    if institution_id is not None:
        query = query.eq("institution_id", str(institution_id))
    return read_rows(
        query.eq("approval_status", "pending")
        .order("created_at")
        .limit(limit)
        .range(offset, offset + limit - 1)
    )


def get_student_for_approval(client, student_id):
    return read_one(
        client.table("students")
        .select(STUDENT_APPROVAL_COLUMNS)
        .eq("student_id", str(student_id))
        .maybe_single()
    )


def set_student_approval_status(client, student_id, institution_id, new_status):
    rows = read_rows(
        client.table("students")
        .update({"approval_status": new_status})
        .eq("student_id", str(student_id))
        .eq("institution_id", str(institution_id))
        .eq("approval_status", "pending")
        .select(STUDENT_APPROVAL_COLUMNS)
    )
    return rows[0] if rows else None


def approve_student_and_provision(
    client, *, student_id, institution_id, actor_user_id, actor_auth_user_id
):
    result = (
        client.rpc(
            "b05_approve_student",
            {
                "p_student_id": str(student_id),
                "p_institution_id": str(institution_id),
                "p_actor_user_id": str(actor_user_id),
                "p_actor_auth_user_id": str(actor_auth_user_id),
            },
        )
        .execute()
        .data
    )
    if isinstance(result, list):
        result = result[0] if result else None
    if not isinstance(result, dict):
        raise RuntimeError("Student approval returned no durable result")
    return result
