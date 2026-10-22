"""Faculty attendance orchestration, roster writes and staged imports.

Parsing, identity, and review validation live in focused attendance modules.
The public service keeps HTTP and existing integration call contracts stable.
"""

import csv
import io
import re
from uuid import UUID

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.services.academics import legacy_rosters
from app.services.academics.academic_packages import translate_error
from app.repositories.shared.query_pages import read_all, read_one, read_rows
from app.schemas.faculty.faculty_attendance import (
    ManualAttendanceRequest, RosterStudentInput, RosterUpdateRequest,
)
from app.services.faculty.attendance import file_parser, validation
from app.services.faculty.attendance.file_parser import validate_import_filename
from app.services.faculty.attendance.identity import _identity_candidates, match_identity
from app.services.faculty.attendance.row_format import (
    MAX_IMPORT_BYTES, MAX_IMPORT_ROWS, MAX_UNPACKED_XLSX_BYTES,
    REQUIRED_IDENTITY_COLUMNS, SUMMARY_COLUMNS, ParsedRows, _clean, _parse_csv,
)


def parse_attendance_file(filename: str, content: bytes, *, values_only: bool = False):
    return file_parser.parse_attendance_file(
        filename, content, values_only=values_only,
        max_unpacked_bytes=MAX_UNPACKED_XLSX_BYTES,
    )


def validate_rows(current_user: dict, section_id: UUID, semester_id: UUID, rows: list[dict]):
    context = _assert_assigned(current_user, section_id)
    return validation.validate_rows(
        current_user, section_id, semester_id, rows, context=context, db=get_admin_client(),
    )


def _assert_assigned(current_user: dict, section_id: UUID, permission: str = "attendance.manage") -> dict:
    from app.services.faculty.faculty_responsibilities import authorize_section
    return authorize_section(current_user, section_id, permission, teaching_only=True)


def list_assignments(current_user: dict) -> list[dict]:
    from app.services.auth.phase81_rbac import list_own_faculty_assignments
    rows = list_own_faculty_assignments(current_user)
    return [{**row, "section_id": row["section"]["section_id"], "semester_id": row["section"]["semester_id"], "academic_year_id": row["section"]["academic_year_id"]} for row in rows]


def list_roster(current_user: dict, section_id: UUID, *, limit: int = 100, offset: int = 0, search: str | None = None) -> list[dict]:
    from app.services.faculty.faculty_responsibilities import authorize_section
    authorize_section(current_user, section_id, "attendance.read")
    query = get_admin_client().table("faculty_attendance_rosters").select('roster_id, register_number, university_roll_number, student_name, email, roster_status, linked_student_id, reconciliation_state, participation_active').eq("institution_id", str(current_user["institution_id"])).eq("section_id", str(section_id)).order("register_number")
    if search:
        search = re.sub(r'[^\w\s@-]', '', search)
        query = query.or_(f"register_number.ilike.%{search}%,student_name.ilike.%{search}%,email.ilike.%{search}%")
    rows = [row for row in read_all(query) if row.get('participation_active', True)]
    return rows[offset:offset + limit]


def create_manual(current_user: dict, section_id: UUID, payload: RosterStudentInput) -> dict:
    context = _assert_assigned(current_user, section_id)
    db = get_admin_client()
    row = payload.model_dump()
    semester = read_one(db.table("semesters").select("semester_number").eq("semester_id", str(context["semester_id"])).maybe_single())
    if semester and semester.get("semester_number") != 1 and not _clean(row.get("university_roll_number")):
        raise AppError("university_roll_number is required except for first semester", 422, "MISSING_REQUIRED_FIELD")
    student, errors = match_identity(str(current_user['institution_id']), row, _identity_candidates(db, str(current_user['institution_id']), [row]))
    if student and any(student.get(field) and str(student[field]) != str(context[field])
                       for field in ('program_id', 'academic_year_id')):
        errors.append('Student belongs to a different branch or academic year')
    if errors:
        raise AppError("; ".join(errors), 422, "IDENTITY_CONFLICT")
    approved = student and student.get('approval_status') == 'approved'
    state = 'UNREGISTERED' if not student else 'PENDING_APPROVAL' if not approved else 'ACTIVE' if student.get('is_active') and student.get('status') == 'active' else 'INACTIVE'
    row.update({"institution_id": str(current_user["institution_id"]), "section_id": str(section_id), "course_offering_id": str(context["course_offering_id"]), "semester_id": str(context["semester_id"]), "created_by": str(current_user["user_id"]), "linked_student_id": student['student_id'] if approved else None, "roster_status": state, 'reconciliation_state': 'LINKED' if approved else 'PENDING' if student else 'NONE'})
    try:
        return read_rows(db.table("faculty_attendance_rosters").insert(row))[0]
    except APIError as exc:
        if exc.code != '23505':
            raise translate_error(exc) from exc
        raise AppError("Roster record already exists for this section", 409, "ROSTER_DUPLICATE") from exc


def update_roster(current_user: dict, roster_id: UUID, payload: RosterUpdateRequest) -> dict:
    db = get_admin_client()
    row = read_one(db.table("faculty_attendance_rosters").select("roster_id, section_id, roster_status").eq("roster_id", str(roster_id)).eq("institution_id", str(current_user["institution_id"])).maybe_single())
    if row is None:
        raise AppError("Roster record not found", 404, "ROSTER_NOT_FOUND")
    _assert_assigned(current_user, UUID(str(row["section_id"])))
    fields = payload.model_dump(exclude_unset=True)
    if 'roster_status' in fields and fields.pop('roster_status') != row['roster_status']:
        raise AppError('Registration state is determined by student registration and approval, not attendance edits', 422, 'REGISTRATION_STATE_MANAGED')
    if not fields:
        raise AppError("Roster update payload is empty", 422, "EMPTY_UPDATE")
    updated = read_rows(db.table("faculty_attendance_rosters").update(fields).eq("roster_id", str(roster_id)).eq("institution_id", str(current_user["institution_id"])).select("*"))
    return updated[0]


def delete_roster(current_user: dict, roster_id: UUID) -> dict:
    db = get_admin_client()
    row = read_one(db.table("faculty_attendance_rosters").select("*").eq("roster_id", str(roster_id)).eq("institution_id", str(current_user["institution_id"])).maybe_single())
    if row is None:
        raise AppError("Roster record not found", 404, "ROSTER_NOT_FOUND")
    _assert_assigned(current_user, UUID(str(row["section_id"])))
    legacy_rosters.delete_roster(db, current_user, roster_id)
    return row


def mark_attendance(current_user: dict, section_id: UUID, payload: ManualAttendanceRequest) -> dict:
    """Create or edit one section/date session with a scope re-check."""
    _assert_assigned(current_user, section_id)
    return _attendance_rpc('mark_faculty_attendance', current_user, {
        'p_section_id': str(section_id), 'p_session_date': payload.session_date.isoformat(),
        'p_attendance': {str(k): v for k, v in payload.attendance.items()}, 'p_notes': payload.notes})


def _attendance_rpc(name: str, user: dict, fields: dict) -> dict:
    from postgrest.exceptions import APIError
    try:
        result = get_admin_client().rpc(name, {'p_actor': str(user['user_id']),
            'p_tenant': str(user['institution_id']), **fields}).execute().data
    except APIError as exc:
        if exc.code == '42501':
            raise AppError('Your teaching assignment, permission or resource ownership is no longer valid', 403, 'FACULTY_SCOPE_DENIED') from exc
        if exc.code in {'23505', '40001'}:
            raise AppError('Attendance changed while you were reviewing it. Reload and review again.', 409, 'ATTENDANCE_CONFLICT') from exc
        if exc.code in {'23514', '22007', '22P02'}:
            raise AppError('Attendance identity or review validation failed; correct the file and review again', 422, 'IMPORT_REVIEW_REQUIRED') from exc
        raise
    if not isinstance(result, dict):
        raise AppError('Invalid attendance database response', 500, 'DATABASE_PROJECTION_INVALID')
    return result


def upload_import(current_user: dict, section_id: UUID, semester_id: UUID, filename: str, content: bytes, ai_confirmed: bool = False, content_type: str | None = None) -> dict:
    _assert_assigned(current_user, section_id)
    if len(content) > MAX_IMPORT_BYTES:
        raise AppError("The attendance file exceeds the 10 MB limit", 413, "FILE_TOO_LARGE")
    safe_name = validate_import_filename(filename, content_type)
    suffix = safe_name.rsplit('.', 1)[-1].lower()
    strategy, rows, needs_ai = parse_attendance_file(safe_name, content)
    if needs_ai and not ai_confirmed:
        raise AppError("This file requires OCR/AI processing. AI may consume tokens; explicit confirmation is required.", 409, "AI_CONFIRMATION_REQUIRED")
    if needs_ai:
        from app.services.faculty.faculty_attendance_extraction import extract_attendance_rows
        rows = extract_attendance_rows(content, suffix)
    summary, reviewed = validate_rows(current_user, section_id, semester_id, rows)
    result = _attendance_rpc('stage_faculty_attendance_import', current_user, {
        'p_section_id': str(section_id), 'p_semester_id': str(semester_id),
        'p_filename': safe_name, 'p_file_type': suffix, 'p_strategy': strategy,
        'p_ai_confirmed': needs_ai and ai_confirmed, 'p_summary': summary, 'p_rows': reviewed})
    return {**result, 'processing_strategy': strategy, 'ai_confirmation_required': needs_ai,
            'summary': summary, 'rows': reviewed}


def review_import(current_user: dict, import_id: UUID) -> dict:
    db = get_admin_client()
    item = read_one(db.table("faculty_attendance_imports").select("*").eq("import_id", str(import_id)).eq("institution_id", str(current_user["institution_id"])).maybe_single())
    if item is None or item.get('test_id'):
        raise AppError("Import not found", 404, "IMPORT_NOT_FOUND")
    from app.services.faculty.faculty_responsibilities import authorize_section
    authorize_section(current_user, UUID(str(item['section_id'])), 'attendance.read')
    rows = read_all(db.table("faculty_attendance_import_rows").select("*").eq("import_id", str(import_id)).order("row_number"))
    return {"import_id": str(import_id), "status": item["status"], "summary": item["summary"], "rows": rows, 'updated_at': item['updated_at']}


def list_imports(current_user: dict, section_id: UUID, *, limit: int = 50, offset: int = 0) -> list[dict]:
    from app.services.faculty.faculty_responsibilities import authorize_section
    authorize_section(current_user, section_id, 'attendance.read')
    return read_rows(get_admin_client().table("faculty_attendance_imports").select("import_id, original_filename, uploaded_by, processing_strategy, ai_confirmation_required, status, summary, created_at, updated_at")
                     .eq('institution_id', str(current_user['institution_id'])).eq('section_id', str(section_id))
                     .is_('test_id', 'null')
                     .order('created_at', desc=True).order('import_id').range(offset, offset + limit - 1))


def error_report(current_user: dict, import_id: UUID) -> str:
    review = review_import(current_user, import_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["row_number", "status", "errors"])
    for row in review["rows"]:
        if row.get("errors"):
            writer.writerow([csv_safe(row.get('row_number')), csv_safe(row.get('validation_status')), csv_safe('; '.join(row['errors']))])
    return output.getvalue()


def csv_safe(value: object) -> str:
    text = str(value or '')
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text


def correct_import_row(user: dict, import_id: UUID, row_number: int, data: dict[str, str]) -> dict:
    item = read_one(get_admin_client().table('faculty_attendance_imports').select('*')
                    .eq('institution_id', str(user['institution_id'])).eq('import_id', str(import_id)).maybe_single())
    if not item:
        raise AppError('Import not found', 404, 'IMPORT_NOT_FOUND')
    from app.services.faculty.faculty_responsibilities import authorize_section
    authorize_section(user, UUID(item['section_id']), 'attendance.manage', teaching_only=True,
                      owner_user_id=item['uploaded_by'], require_owner=True)
    review = review_import(user, import_id)
    if item['status'] == 'IMPORTED' or row_number not in {r['row_number'] for r in review['rows']}:
        raise AppError('This staging row cannot be edited', 409, 'IMPORT_NOT_EDITABLE')
    raw = [data if r['row_number'] == row_number else r['raw_data'] for r in review['rows'] if r['row_number'] >= 2]
    summary, rows = validate_rows(user, UUID(item['section_id']), UUID(item['semester_id']), raw)
    _attendance_rpc('review_faculty_attendance_import', user, {'p_import_id': str(import_id),
        'p_summary': summary, 'p_rows': rows, 'p_expected_updated_at': item['updated_at']})
    return review_import(user, import_id)


def commit_import(current_user: dict, import_id: UUID) -> dict:
    review = review_import(current_user, import_id)
    if review["summary"].get("errors", 0) or review["summary"].get("conflicts", 0) or review["summary"].get("duplicates", 0):
        raise AppError("Correct all errors, duplicates, and conflicts before importing", 422, "IMPORT_REVIEW_REQUIRED")
    db = get_admin_client()
    item = read_one(db.table("faculty_attendance_imports").select("section_id, status, uploaded_by").eq("import_id", str(import_id)).eq("institution_id", str(current_user["institution_id"])).maybe_single())
    if item is None:
        raise AppError("Import not found", 404, "IMPORT_NOT_FOUND")
    if item["status"] == "IMPORTED":
        raise AppError("This import has already been committed", 409, "IMPORT_ALREADY_COMMITTED")
    from app.services.faculty.faculty_responsibilities import authorize_section
    authorize_section(current_user, UUID(str(item["section_id"])), "attendance.manage", teaching_only=True,
                                owner_user_id=str(item["uploaded_by"]), require_owner=True)
    full_item = read_one(db.table('faculty_attendance_imports').select('semester_id, updated_at')
                         .eq('import_id', str(import_id)).eq('institution_id', str(current_user['institution_id'])).maybe_single())
    _summary, rows = validate_rows(current_user, UUID(item['section_id']), UUID(full_item['semester_id']),
                                 [r['raw_data'] for r in review['rows'] if r['row_number'] >= 2])
    if not rows or any(r['errors'] for r in rows):
        raise AppError('The import no longer validates. Correct and review it again.', 422, 'IMPORT_REVIEW_REQUIRED')
    return _attendance_rpc('commit_faculty_attendance_import', current_user, {
        'p_import_id': str(import_id), 'p_expected_updated_at': review['updated_at'], 'p_rows': rows})
