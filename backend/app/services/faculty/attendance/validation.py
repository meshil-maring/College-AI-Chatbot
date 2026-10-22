"""Import-row eligibility, academic context and identity review."""

import math
from datetime import date
from uuid import UUID

from app.core.errors import AppError
from app.repositories.shared.query_pages import read_all, read_one
from app.services.academics import managed_rosters
from app.services.faculty.attendance.identity import _identity_candidates, match_identity
from app.services.faculty.attendance.row_format import (
    ALLOWED_COLUMNS, ATTENDANCE_STATUSES, MAX_IMPORT_ROWS,
    REQUIRED_IDENTITY_COLUMNS, SUMMARY_COLUMNS, ParsedRows, _clean, _normalize_row,
)

def _number(value: str, label: str, *, integer: bool = False) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value.rstrip("%").strip())
    except ValueError:
        raise ValueError(f"{label} must be numeric") from None
    if not math.isfinite(parsed):
        raise ValueError(f"{label} must be finite")
    if integer and not parsed.is_integer():
        raise ValueError(f"{label} must be a whole number")
    if integer and '%' in value:
        raise ValueError(f'{label} must be a count, not a percentage')
    return parsed


def _validate_attendance_fields(normalized: dict[str, str], errors: list[str]) -> dict[str, float | str] | None:
    status = normalized.get("status", "").lower()
    if status and status not in ATTENDANCE_STATUSES:
        errors.append("status must be one of present, absent, late, excused")
    if status:
        try:
            date.fromisoformat(normalized.get('session_date', ''))
        except ValueError:
            errors.append('session_date (YYYY-MM-DD) is required for a recorded status')
    values: dict[str, float | str] = {"status": status} if status else {}
    fields = {
        "classes_conducted": (True, 0, None),
        "classes_present": (True, 0, None),
        "classes_absent": (True, 0, None),
        "attendance_percentage": (False, 0, 100),
        "attendance": (False, 0, 100),
    }
    for field, (integer, minimum, maximum) in fields.items():
        if not normalized.get(field):
            continue
        try:
            value = _number(normalized[field], field, integer=integer)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if value is not None and (value < minimum or (maximum is not None and value > maximum)):
            errors.append(f"{field} must be between {minimum} and {maximum}")
        if value is not None:
            values[field] = int(value) if integer else value
    conducted = values.get("classes_conducted")
    present = values.get("classes_present")
    absent = values.get("classes_absent")
    for field in ('classes_present', 'classes_absent'):
        if isinstance(conducted, (int, float)) and isinstance(values.get(field), (int, float)) and values[field] > conducted:
            errors.append(f'{field} cannot exceed classes_conducted')
    if isinstance(conducted, (int, float)) and isinstance(present, (int, float)) and isinstance(absent, (int, float)) and present + absent > conducted:
        errors.append("classes_present plus classes_absent cannot exceed classes_conducted")
    if not values:
        errors.append("attendance or attendance summary is required")
    return values or None


def validate_rows(current_user: dict, section_id: UUID, semester_id: UUID, rows: list[dict], *, context: dict, db) -> tuple[dict, list[dict]]:
    if len(rows) > MAX_IMPORT_ROWS:
        raise AppError('Imports are limited to 500 rows', 413, 'TOO_MANY_ROWS')
    if str(context["semester_id"]) != str(semester_id):
        raise AppError("The selected semester does not match the assigned section", 422, "ACADEMIC_CONTEXT_MISMATCH")
    semester = read_one(db.table("semesters").select("semester_number").eq("semester_id", str(context["semester_id"])).maybe_single())
    first_semester = semester is not None and semester.get("semester_number") == 1
    seen_registers: set[str] = set()
    seen_rolls: set[str] = set()
    reviewed: list[dict] = []
    parsed_rows = rows if isinstance(rows, ParsedRows) else ParsedRows(rows)
    candidates = _identity_candidates(db, str(current_user['institution_id']), parsed_rows)
    existing = read_all(db.table('faculty_attendance_rosters').select('roster_id, register_number, university_roll_number, linked_student_id, participation_active')
                        .eq('institution_id', str(current_user['institution_id'])).eq('section_id', str(section_id)).order('roster_id'))
    managed = managed_rosters.contexts(db, str(current_user['institution_id']), existing)
    headers = set(parsed_rows.headers)
    missing_headers = REQUIRED_IDENTITY_COLUMNS - headers if headers else set()
    if headers and not (SUMMARY_COLUMNS & headers):
        missing_headers.add("attendance")
    if missing_headers:
        reviewed.append({"row_number": 1, "raw_data": {}, "normalized_data": {}, "validation_status": "ERROR", "errors": [f"missing required column: {column}" for column in sorted(missing_headers)], "student_id": None})
    if not parsed_rows and not missing_headers:
        reviewed.append({'row_number': 1, 'raw_data': {}, 'normalized_data': {}, 'validation_status': 'ERROR', 'errors': ['No attendance rows were extracted'], 'student_id': None})
    for number, raw in enumerate(parsed_rows, 2):
        normalized = _normalize_row(raw)
        errors: list[str] = []
        errors.extend(f'unexpected column: {key}' for key in normalized if key not in ALLOWED_COLUMNS)
        for key, value in normalized.items():
            if len(value) > (256 if key == 'student_name' else 2000 if key == 'address' else 128):
                errors.append(f'{key} exceeds the field length limit')
            if value.lstrip().startswith(('=', '+', '@')) or (value.lstrip().startswith('-') and key not in SUMMARY_COLUMNS):
                errors.append(f'{key} contains an unsafe spreadsheet formula prefix')
        register = normalized.get("register_number", "").lower()
        roll = normalized.get("university_roll_number", "").lower()
        roster_matches = [r for r in existing if r['register_number'] == normalized.get('register_number') or
                          (roll and r.get('university_roll_number') == normalized.get('university_roll_number'))]
        matched = roster_matches[0] if len(roster_matches) == 1 else None
        row_first_semester = managed_rosters.first_study_semester(matched, managed, legacy=first_semester)
        if not register:
            errors.append("register_number is required")
        if not normalized.get("student_name"):
            errors.append("student_name is required")
        if not row_first_semester and not roll:
            errors.append("university_roll_number is required except for first semester")
        if (register and register in seen_registers) or (roll and roll in seen_rolls):
            errors.append("duplicate record in upload")
        if register:
            seen_registers.add(register)
        if roll:
            seen_rolls.add(roll)
        if normalized.get('email'):
            from email_validator import EmailNotValidError, validate_email
            try:
                validate_email(normalized['email'], check_deliverability=False)
            except EmailNotValidError:
                errors.append('email is malformed')
        imported_summary = _validate_attendance_fields(normalized, errors)
        student, identity_errors = match_identity(str(current_user['institution_id']), normalized, candidates)
        student, scope_errors = managed_rosters.academic_identity(student, matched, context, managed)
        identity_errors.extend(scope_errors)
        if len(roster_matches) > 1 or any(
            r['register_number'] != normalized.get('register_number') or
            (roll and r.get('university_roll_number') and r['university_roll_number'] != normalized.get('university_roll_number')) or
            (r.get('linked_student_id') and (not student or r['linked_student_id'] != student['student_id'])) for r in roster_matches):
            identity_errors.append('Existing roster identity conflicts; automatic reassociation is prohibited')
        errors.extend(identity_errors)
        if student and ((student.get('program_id') and str(student['program_id']) != str(context['program_id']))
                        or (student.get('academic_year_id') and str(student['academic_year_id']) != str(context['academic_year_id']))):
            errors.append('matched student is outside the selected program/academic year')
        if errors:
            status = "DUPLICATE" if any("duplicate" in error for error in errors) else ("CONFLICT" if identity_errors or any("matched student" in error for error in errors) else "ERROR")
        else:
            status = "UPDATE" if student else "NEW"
        warnings = ['University Roll Number is missing (permitted in first semester)'] if row_first_semester and not roll else []
        if imported_summary and not normalized.get('status'):
            warnings.append('Summary retained as provenance; no session records will be created')
        reviewed.append({"row_number": number, "raw_data": raw, "normalized_data": normalized, "validation_status": status, "errors": errors, 'warnings': warnings, "student_id": student.get("student_id") if student and not errors else None, "imported_summary": imported_summary})
    summary = {key: sum(1 for row in reviewed if row["validation_status"] == key) for key in ("NEW", "UPDATE", "DUPLICATE", "CONFLICT", "ERROR")}
    summary.update({"total_rows": len(parsed_rows), "valid": summary["NEW"] + summary["UPDATE"], "new_records": summary["NEW"], "updates": summary["UPDATE"], "duplicates": summary["DUPLICATE"], "conflicts": summary["CONFLICT"], "errors": summary["ERROR"]})
    return summary, reviewed


