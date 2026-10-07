"""Faculty attendance orchestration over the existing academic models.

Imported data is staged and reviewed before it is promoted to the section
roster. Registered-student identity, tenant, section scope, and semester
context are resolved server-side. Imported percentage/count summaries are
kept as provenance and are never converted into invented session rows.
"""

import csv
import io
import math
import posixpath
import zipfile
from datetime import datetime, timezone
from email.utils import parseaddr
from pathlib import PurePath
from typing import Iterable
from uuid import UUID
import xml.etree.ElementTree as ET

from pypdf import PdfReader

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin_academics import (
    get_student_by_register_number,
    get_student_by_university_roll_number,
)
from app.schemas.faculty_attendance import RosterStudentInput, RosterUpdateRequest
from app.schemas.faculty_attendance import ManualAttendanceRequest

MAX_IMPORT_BYTES = 10 * 1024 * 1024
MAX_UNPACKED_XLSX_BYTES = 50 * 1024 * 1024
ALLOWED_SUFFIXES = {"csv", "xls", "xlsx", "pdf", "png", "jpg", "jpeg", "webp"}
ATTENDANCE_STATUSES = {"present", "absent", "late", "excused"}
REQUIRED_IDENTITY_COLUMNS = {"register_number", "student_name"}
SUMMARY_COLUMNS = {
    "attendance",
    "attendance_percentage",
    "classes_conducted",
    "classes_present",
    "classes_absent",
    "status",
}


class ParsedRows(list[dict[str, str]]):
    """A list that retains headers for server-side validation."""

    headers: tuple[str, ...]

    def __init__(self, rows: Iterable[dict[str, str]] = (), headers: Iterable[str] = ()):
        super().__init__(rows)
        self.headers = tuple(headers)


def _clean(value: object) -> str:
    return str(value or "").strip()


def _column_name(value: object) -> str:
    return _clean(value).lstrip("\ufeff").lower().replace(" ", "_")


def _canonical_header(value: object) -> str:
    name = _column_name(value)
    return {"name": "student_name", "percentage": "attendance"}.get(name, name)


def _normalize_row(row: dict[object, object]) -> dict[str, str]:
    normalized = {_column_name(key): _clean(value) for key, value in row.items() if key is not None}
    if "student_name" not in normalized and "name" in normalized:
        normalized["student_name"] = normalized["name"]
    if "attendance" not in normalized and "percentage" in normalized:
        normalized["attendance"] = normalized["percentage"]
    return normalized


def _parse_xlsx(content: bytes) -> ParsedRows:
    """Read the first worksheet without executing workbook content."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            if any(name.startswith("/") or ".." in PurePath(name).parts for name in names):
                raise AppError("The workbook contains an unsafe internal path", 422, "MALFORMED_FILE")
            if sum(info.file_size for info in archive.infolist()) > MAX_UNPACKED_XLSX_BYTES:
                raise AppError("The workbook expands beyond the allowed size", 413, "FILE_TOO_LARGE")
            if "xl/workbook.xml" not in names or "xl/_rels/workbook.xml.rels" not in names:
                raise AppError("The XLSX workbook structure is invalid", 422, "MALFORMED_FILE")
            shared: list[str] = []
            if "xl/sharedStrings.xml" in names:
                root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = ["".join(node.itertext()) for node in root]
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            relmap = {r.attrib["Id"]: r.attrib["Target"] for r in rels}
            ns = {
                "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
                "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
            }
            sheet = workbook.find("m:sheets/m:sheet", ns)
            if sheet is None:
                return ParsedRows()
            target = relmap[sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]]
            target = posixpath.normpath(posixpath.join("xl", target)) if not target.startswith("xl/") else target
            if target not in names or not target.startswith("xl/"):
                raise AppError("The XLSX worksheet path is invalid", 422, "MALFORMED_FILE")
            root = ET.fromstring(archive.read(target))
            rows: list[dict[int, str]] = []
            for row in root.findall(".//m:sheetData/m:row", ns):
                values: dict[int, str] = {}
                for cell in row.findall("m:c", ns):
                    ref = cell.attrib.get("r", "A1")
                    letters = "".join(char for char in ref if char.isalpha()).upper()
                    index = 0
                    for char in letters:
                        index = index * 26 + ord(char) - ord("A") + 1
                    value = cell.find("m:v", ns)
                    text = "" if value is None else value.text or ""
                    if cell.attrib.get("t") == "s" and text.isdigit():
                        shared_index = int(text)
                        text = shared[shared_index] if shared_index < len(shared) else ""
                    values[max(index - 1, 0)] = text
                rows.append(values)
    except AppError:
        raise
    except (KeyError, ValueError, ET.ParseError, zipfile.BadZipFile, IndexError) as exc:
        raise AppError("The XLSX workbook is malformed", 422, "MALFORMED_FILE") from exc
    if not rows:
        return ParsedRows()
    width = max((max(row, default=-1) for row in rows), default=-1) + 1
    headers = tuple(_canonical_header(rows[0].get(index, "")) for index in range(width))
    return ParsedRows(
        (_normalize_row({headers[index]: row.get(index, "") for index in range(width)}) for row in rows[1:]),
        headers,
    )


def parse_attendance_file(filename: str, content: bytes) -> tuple[str, list[dict[str, str]], bool]:
    """Return ``(strategy, rows, ai_confirmation_required)``."""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix not in ALLOWED_SUFFIXES:
        raise AppError("Unsupported attendance file. Use CSV, XLSX, PDF, or an image.", 422, "UNSUPPORTED_FILE")
    if not content:
        raise AppError("The attendance file is empty", 422, "EMPTY_FILE")
    if suffix == "csv":
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            if reader.fieldnames is None:
                raise AppError("The CSV file has no header row", 422, "MISSING_REQUIRED_COLUMNS")
            rows = ParsedRows((_normalize_row(row) for row in reader), (_canonical_header(key) for key in reader.fieldnames))
            return "CSV", rows, False
        except UnicodeDecodeError as exc:
            raise AppError("The CSV file must be UTF-8 encoded", 422, "MALFORMED_FILE") from exc
    if suffix == "xlsx":
        if not content.startswith(b"PK"):
            raise AppError("The XLSX file signature is invalid", 422, "MALFORMED_FILE")
        return "XLSX", _parse_xlsx(content), False
    if suffix == "xls":
        try:
            decoded = content.decode("utf-8-sig")
            dialect = csv.Sniffer().sniff(decoded[:4096], delimiters=",\t;")
            reader = csv.DictReader(io.StringIO(decoded), dialect=dialect)
            if reader.fieldnames is None:
                raise AppError("The XLS file has no header row", 422, "MISSING_REQUIRED_COLUMNS")
            return "XLS", ParsedRows((_normalize_row(row) for row in reader), (_canonical_header(key) for key in reader.fieldnames)), False
        except AppError:
            raise
        except (UnicodeDecodeError, csv.Error) as exc:
            raise AppError("This legacy XLS workbook could not be read deterministically; convert it to XLSX or CSV", 422, "UNSUPPORTED_FILE") from exc
    if suffix == "pdf":
        if not content.startswith(b"%PDF"):
            raise AppError("The PDF file signature is invalid", 422, "MALFORMED_FILE")
        try:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
        except Exception as exc:
            raise AppError("The PDF could not be read safely", 422, "MALFORMED_FILE") from exc
        if not text.strip():
            return "OCR_AI", ParsedRows(), True
        rows = []
        for line in text.splitlines():
            columns = [part.strip() for part in line.split(",")]
            if len(columns) >= 3:
                rows.append(_normalize_row({"register_number": columns[0], "university_roll_number": columns[1], "student_name": columns[2]}))
        return "PDF_TEXT", ParsedRows(rows), False
    # OCR/AI is a separately-confirmed integration. No provider is invoked by
    # parsing, and the caller must explicitly confirm before continuing.
    return "OCR_AI", ParsedRows(), True


def _assert_assigned(current_user: dict, section_id: UUID) -> dict:
    db = get_admin_client()
    tenant = str(current_user["institution_id"])
    assignment = (
        db.table("faculty_section_assignments")
        .select("assignment_id")
        .eq("institution_id", tenant)
        .eq("faculty_user_id", str(current_user["user_id"]))
        .eq("section_id", str(section_id))
        .is_("revoked_at", "null")
        .maybe_single()
        .execute()
        .data
    )
    if assignment is None:
        raise AppError("You are not assigned to this active section", 403, "FACULTY_SCOPE_DENIED")
    section = db.table("sections").select("section_id, course_offering_id, is_active").eq("section_id", str(section_id)).maybe_single().execute().data
    if section is None or not section.get("is_active"):
        raise AppError("Section is not active", 403, "SECTION_INACTIVE")
    offering = db.table("course_offerings").select("course_offering_id, academic_year_id, semester_id, is_active, courses!inner(department_id, departments!inner(institution_id))").eq("course_offering_id", str(section["course_offering_id"])).eq("is_active", True).maybe_single().execute().data
    course = offering.get("courses", {}) if offering else {}
    if isinstance(course, list):
        course = course[0] if course else {}
    department = course.get("departments", {}) if isinstance(course, dict) else {}
    if isinstance(department, list):
        department = department[0] if department else {}
    if offering is None or department.get("institution_id") != tenant:
        raise AppError("Section is outside your institution", 403, "TENANT_MISMATCH")
    return {**section, **offering, "institution_id": tenant}


def _identity(db, institution_id: str, row: dict[str, str]) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    register = _clean(row.get("register_number"))
    roll = _clean(row.get("university_roll_number")) or None
    by_register = get_student_by_register_number(db, institution_id, register) if register else None
    by_roll = get_student_by_university_roll_number(db, institution_id, roll) if roll else None
    if by_register and by_roll and by_register["student_id"] != by_roll["student_id"]:
        errors.append("register number and university roll number match different students")
        return None, errors
    return by_register or by_roll, errors


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
    return parsed


def _validate_attendance_fields(normalized: dict[str, str], errors: list[str]) -> dict[str, float | str] | None:
    status = normalized.get("status", "").lower()
    if status and status not in ATTENDANCE_STATUSES:
        errors.append("status must be one of present, absent, late, excused")
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
    if isinstance(conducted, (int, float)) and isinstance(present, (int, float)) and isinstance(absent, (int, float)) and present + absent > conducted:
        errors.append("classes_present plus classes_absent cannot exceed classes_conducted")
    if not (status or any(field in normalized for field in SUMMARY_COLUMNS - {"status"})):
        errors.append("attendance or attendance summary is required")
    return values or None


def validate_rows(current_user: dict, section_id: UUID, semester_id: UUID, rows: list[dict]) -> tuple[dict, list[dict]]:
    context = _assert_assigned(current_user, section_id)
    if str(context["semester_id"]) != str(semester_id):
        raise AppError("The selected semester does not match the assigned section", 422, "ACADEMIC_CONTEXT_MISMATCH")
    db = get_admin_client()
    semester = db.table("semesters").select("semester_number").eq("semester_id", str(context["semester_id"])).maybe_single().execute().data
    first_semester = semester is not None and semester.get("semester_number") == 1
    seen_registers: set[str] = set()
    seen_rolls: set[str] = set()
    reviewed: list[dict] = []
    parsed_rows = rows if isinstance(rows, ParsedRows) else ParsedRows(rows)
    headers = set(parsed_rows.headers)
    missing_headers = REQUIRED_IDENTITY_COLUMNS - headers if headers else set()
    if headers and not (SUMMARY_COLUMNS & headers):
        missing_headers.add("attendance")
    if missing_headers:
        reviewed.append({"row_number": 1, "raw_data": {}, "normalized_data": {}, "validation_status": "ERROR", "errors": [f"missing required column: {column}" for column in sorted(missing_headers)], "student_id": None})
    for number, raw in enumerate(parsed_rows, 2):
        normalized = _normalize_row(raw)
        errors: list[str] = []
        register = normalized.get("register_number", "").lower()
        roll = normalized.get("university_roll_number", "").lower()
        if not register:
            errors.append("register_number is required")
        if not normalized.get("student_name"):
            errors.append("student_name is required")
        if not first_semester and not roll:
            errors.append("university_roll_number is required except for first semester")
        if (register and register in seen_registers) or (roll and roll in seen_rolls):
            errors.append("duplicate record in upload")
        if register:
            seen_registers.add(register)
        if roll:
            seen_rolls.add(roll)
        if normalized.get("email") and "@" not in parseaddr(normalized["email"])[1]:
            errors.append("email is malformed")
        imported_summary = _validate_attendance_fields(normalized, errors)
        student, identity_errors = _identity(db, str(current_user["institution_id"]), normalized)
        errors.extend(identity_errors)
        if student and not student.get("is_active", True):
            errors.append("matched student is inactive")
        if student and student.get("approval_status") not in {"approved", None}:
            errors.append("matched student is not approved")
        if errors:
            status = "DUPLICATE" if any("duplicate" in error for error in errors) else ("CONFLICT" if identity_errors or any("matched student" in error for error in errors) else "ERROR")
        else:
            status = "UPDATE" if student else "NEW"
        reviewed.append({"row_number": number, "raw_data": raw, "normalized_data": normalized, "validation_status": status, "errors": errors, "student_id": student.get("student_id") if student and not errors else None, "imported_summary": imported_summary})
    summary = {key: sum(1 for row in reviewed if row["validation_status"] == key) for key in ("NEW", "UPDATE", "DUPLICATE", "CONFLICT", "ERROR")}
    summary.update({"total_rows": len(parsed_rows), "valid": summary["NEW"] + summary["UPDATE"], "new_records": summary["NEW"], "updates": summary["UPDATE"], "duplicates": summary["DUPLICATE"], "conflicts": summary["CONFLICT"], "errors": summary["ERROR"]})
    return summary, reviewed


def list_assignments(current_user: dict) -> list[dict]:
    from app.services.phase81_rbac import list_own_faculty_assignments
    rows = list_own_faculty_assignments(current_user)
    return [{**row, "section_id": row["section"]["section_id"], "semester_id": row["section"]["semester_id"], "academic_year_id": row["section"]["academic_year_id"]} for row in rows]


def list_roster(current_user: dict, section_id: UUID, *, limit: int = 100, offset: int = 0, search: str | None = None) -> list[dict]:
    _assert_assigned(current_user, section_id)
    query = get_admin_client().table("faculty_attendance_rosters").select("*").eq("institution_id", str(current_user["institution_id"])).eq("section_id", str(section_id)).order("register_number").range(offset, offset + limit - 1)
    if search:
        query = query.or_(f"register_number.ilike.%{search}%,student_name.ilike.%{search}%,email.ilike.%{search}%")
    return query.execute().data


def create_manual(current_user: dict, section_id: UUID, payload: RosterStudentInput) -> dict:
    context = _assert_assigned(current_user, section_id)
    db = get_admin_client()
    row = payload.model_dump()
    semester = db.table("semesters").select("semester_number").eq("semester_id", str(context["semester_id"])).maybe_single().execute().data
    if semester and semester.get("semester_number") != 1 and not _clean(row.get("university_roll_number")):
        raise AppError("university_roll_number is required except for first semester", 422, "MISSING_REQUIRED_FIELD")
    student, errors = _identity(db, str(current_user["institution_id"]), row)
    if errors:
        raise AppError("; ".join(errors), 422, "IDENTITY_CONFLICT")
    row.update({"institution_id": current_user["institution_id"], "section_id": section_id, "course_offering_id": context["course_offering_id"], "semester_id": context["semester_id"], "created_by": current_user["user_id"], "linked_student_id": student.get("student_id") if student else None, "roster_status": "ACTIVE" if student and student.get("approval_status") in {"approved", None} else "UNREGISTERED"})
    try:
        return db.table("faculty_attendance_rosters").insert(row).execute().data[0]
    except Exception as exc:
        raise AppError("Roster record already exists for this section", 409, "ROSTER_DUPLICATE") from exc


def update_roster(current_user: dict, roster_id: UUID, payload: RosterUpdateRequest) -> dict:
    db = get_admin_client()
    row = db.table("faculty_attendance_rosters").select("roster_id, section_id").eq("roster_id", str(roster_id)).eq("institution_id", str(current_user["institution_id"])).maybe_single().execute().data
    if row is None:
        raise AppError("Roster record not found", 404, "ROSTER_NOT_FOUND")
    _assert_assigned(current_user, UUID(str(row["section_id"])))
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise AppError("Roster update payload is empty", 422, "EMPTY_UPDATE")
    updated = db.table("faculty_attendance_rosters").update(fields).eq("roster_id", str(roster_id)).eq("institution_id", str(current_user["institution_id"])).select("*").execute().data
    return updated[0]


def delete_roster(current_user: dict, roster_id: UUID) -> dict:
    db = get_admin_client()
    row = db.table("faculty_attendance_rosters").select("*").eq("roster_id", str(roster_id)).eq("institution_id", str(current_user["institution_id"])).maybe_single().execute().data
    if row is None:
        raise AppError("Roster record not found", 404, "ROSTER_NOT_FOUND")
    _assert_assigned(current_user, UUID(str(row["section_id"])))
    db.table("faculty_attendance_rosters").delete().eq("roster_id", str(roster_id)).eq("institution_id", str(current_user["institution_id"])).execute()
    return row


def mark_attendance(current_user: dict, section_id: UUID, payload: ManualAttendanceRequest) -> dict:
    """Create or edit one section/date session with a scope re-check."""
    context = _assert_assigned(current_user, section_id)
    db = get_admin_client()
    requested = [str(roster_id) for roster_id in payload.attendance]
    roster_rows = []
    if requested:
        roster_rows = db.table("faculty_attendance_rosters").select("roster_id, linked_student_id").eq("institution_id", str(current_user["institution_id"])).eq("section_id", str(section_id)).in_("roster_id", requested).execute().data
        if len(roster_rows) != len(requested):
            raise AppError("Attendance contains a student outside this section", 403, "FACULTY_SCOPE_DENIED")
    session_response = db.table("faculty_attendance_sessions").upsert({"institution_id": current_user["institution_id"], "section_id": section_id, "course_offering_id": context["course_offering_id"], "session_date": payload.session_date.isoformat(), "conducted_by": current_user["user_id"]}, on_conflict="section_id,session_date").execute()
    if not session_response.data:
        raise AppError("Attendance session could not be created", 409, "ATTENDANCE_SESSION_FAILED")
    session = session_response.data[0]
    records = [{"session_id": session["session_id"], "roster_id": str(roster_id), "status": status, "notes": payload.notes} for roster_id, status in payload.attendance.items()]
    if records:
        db.table("faculty_attendance_records").upsert(records, on_conflict="session_id,roster_id").execute()
    # Keep the existing student-facing attendance table in sync for linked
    # students. Unregistered roster rows remain in the faculty tables until
    # reconciliation can safely link them.
    linked = {str(row["roster_id"]): row.get("linked_student_id") for row in roster_rows}
    student_records = [{"student_id": linked[str(roster_id)], "section_id": str(section_id), "academic_year_id": context["academic_year_id"], "semester_id": context["semester_id"], "date": payload.session_date.isoformat(), "status": status, "notes": payload.notes, "institution_id": current_user["institution_id"]} for roster_id, status in payload.attendance.items() if linked.get(str(roster_id))]
    if student_records:
        db.table("student_attendance").upsert(student_records, on_conflict="student_id,section_id,date").execute()
    return {"session_id": session["session_id"], "record_count": len(records), "updated_existing_student_records": len(student_records)}


def upload_import(current_user: dict, section_id: UUID, semester_id: UUID, filename: str, content: bytes, ai_confirmed: bool = False, content_type: str | None = None) -> dict:
    context = _assert_assigned(current_user, section_id)
    if len(content) > MAX_IMPORT_BYTES:
        raise AppError("The attendance file exceeds the 10 MB limit", 413, "FILE_TOO_LARGE")
    safe_name = PurePath(filename).name
    if not filename or safe_name != filename or filename in {".", ".."}:
        raise AppError("The attendance filename is unsafe", 422, "UNSAFE_FILENAME")
    strategy, rows, needs_ai = parse_attendance_file(safe_name, content)
    if needs_ai and not ai_confirmed:
        raise AppError("This file requires OCR/AI processing. AI may consume tokens; explicit confirmation is required.", 409, "AI_CONFIRMATION_REQUIRED")
    if content_type and content_type in {"application/x-msdownload", "application/zip"}:
        raise AppError("The uploaded MIME type is not allowed", 422, "INVALID_MIME")
    summary, reviewed = validate_rows(current_user, section_id, semester_id, rows)
    db = get_admin_client()
    import_row = db.table("faculty_attendance_imports").insert({"institution_id": current_user["institution_id"], "section_id": section_id, "course_offering_id": context["course_offering_id"], "academic_year_id": context["academic_year_id"], "semester_id": context["semester_id"], "uploaded_by": current_user["user_id"], "original_filename": safe_name, "file_type": safe_name.rsplit(".", 1)[-1].lower(), "processing_strategy": strategy, "ai_confirmation_required": needs_ai, "ai_confirmed_at": datetime.now(timezone.utc).isoformat() if needs_ai and ai_confirmed else None, "status": "VALIDATED", "summary": summary}).execute().data[0]
    staged = [{"import_id": import_row["import_id"], "row_number": row["row_number"], "raw_data": row["raw_data"], "normalized_data": {**row["normalized_data"], "_imported_summary": row.get("imported_summary")}, "validation_status": row["validation_status"], "errors": row["errors"]} for row in reviewed]
    if staged:
        db.table("faculty_attendance_import_rows").insert(staged).execute()
    return {"import_id": import_row["import_id"], "processing_strategy": strategy, "ai_confirmation_required": needs_ai, "summary": summary, "rows": reviewed}


def review_import(current_user: dict, import_id: UUID) -> dict:
    db = get_admin_client()
    item = db.table("faculty_attendance_imports").select("*").eq("import_id", str(import_id)).eq("institution_id", str(current_user["institution_id"])).maybe_single().execute().data
    if item is None:
        raise AppError("Import not found", 404, "IMPORT_NOT_FOUND")
    _assert_assigned(current_user, UUID(str(item["section_id"])))
    rows = db.table("faculty_attendance_import_rows").select("*").eq("import_id", str(import_id)).order("row_number").execute().data
    return {"import_id": str(import_id), "status": item["status"], "summary": item["summary"], "rows": rows}


def list_imports(current_user: dict, section_id: UUID) -> list[dict]:
    _assert_assigned(current_user, section_id)
    return get_admin_client().table("faculty_attendance_imports").select("import_id, original_filename, uploaded_by, processing_strategy, ai_confirmation_required, status, summary, created_at, updated_at").eq("institution_id", str(current_user["institution_id"])).eq("section_id", str(section_id)).order("created_at", desc=True).limit(100).execute().data


def error_report(current_user: dict, import_id: UUID) -> str:
    review = review_import(current_user, import_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["row_number", "status", "errors", "raw_data"])
    for row in review["rows"]:
        if row.get("errors"):
            writer.writerow([row.get("row_number"), row.get("validation_status"), "; ".join(row["errors"]), row.get("raw_data")])
    return output.getvalue()


def commit_import(current_user: dict, import_id: UUID) -> dict:
    review = review_import(current_user, import_id)
    if review["summary"].get("errors", 0) or review["summary"].get("conflicts", 0) or review["summary"].get("duplicates", 0):
        raise AppError("Correct all errors, duplicates, and conflicts before importing", 422, "IMPORT_REVIEW_REQUIRED")
    db = get_admin_client()
    item = db.table("faculty_attendance_imports").select("section_id, status").eq("import_id", str(import_id)).eq("institution_id", str(current_user["institution_id"])).maybe_single().execute().data
    if item is None:
        raise AppError("Import not found", 404, "IMPORT_NOT_FOUND")
    if item["status"] == "IMPORTED":
        raise AppError("This import has already been committed", 409, "IMPORT_ALREADY_COMMITTED")
    context = _assert_assigned(current_user, UUID(str(item["section_id"])))
    created = 0
    for row in review["rows"]:
        data = row.get("normalized_data") or {}
        student, _ = _identity(db, str(current_user["institution_id"]), data)
        record = {"institution_id": current_user["institution_id"], "section_id": item["section_id"], "course_offering_id": context["course_offering_id"], "semester_id": context["semester_id"], "created_by": current_user["user_id"], "linked_student_id": student.get("student_id") if student else None, "roster_status": "ACTIVE" if student and student.get("approval_status") in {"approved", None} else "UNREGISTERED", "source_metadata": {"import_id": str(import_id), "processing": "validated_import"}, "imported_summary": data.get("_imported_summary"), **{key: data.get(key) for key in ("register_number", "university_roll_number", "student_name", "email", "address")}}
        db.table("faculty_attendance_rosters").upsert(record, on_conflict="institution_id,section_id,register_number").execute()
        created += 1
    db.table("faculty_attendance_imports").update({"status": "IMPORTED"}).eq("import_id", str(import_id)).eq("institution_id", str(current_user["institution_id"])).execute()
    return {"import_id": str(import_id), "imported_rows": created, "status": "IMPORTED"}
