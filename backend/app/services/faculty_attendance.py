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
import re
import struct
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Iterable, Mapping
from datetime import date
from pathlib import PurePath
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.admin_academics import (
    get_student_by_register_number,
    get_student_by_university_roll_number,
)
from app.repositories.query_pages import read_all, read_one, read_rows
from app.schemas.faculty_attendance import (
    ManualAttendanceRequest,
    RosterStudentInput,
    RosterUpdateRequest,
)

MAX_IMPORT_BYTES = 10 * 1024 * 1024
MAX_UNPACKED_XLSX_BYTES = 50 * 1024 * 1024
MAX_IMPORT_ROWS = 500
MAX_COLUMNS = 20
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
ALLOWED_COLUMNS = REQUIRED_IDENTITY_COLUMNS | SUMMARY_COLUMNS | {'university_roll_number', 'email', 'address', 'session_date'}


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


def _normalize_row(row: Mapping[Any, Any]) -> dict[str, str]:
    return {_canonical_header(key): _clean(value) for key, value in row.items() if key is not None and _clean(value)}


def _parse_csv(text: str, *, dialect='excel') -> ParsedRows:
    if '\x00' in text:
        raise AppError('The table contains binary data', 422, 'MALFORMED_FILE')
    try:
        reader = csv.DictReader(io.StringIO(text), dialect=dialect, strict=True)
        headers = tuple(_canonical_header(k) for k in reader.fieldnames or [])
        if not headers or len(headers) > MAX_COLUMNS or len(headers) != len(set(headers)) or '' in headers:
            raise AppError('The table must have unique, nonblank column names (maximum 20)', 422, 'MISSING_REQUIRED_COLUMNS')
        rows = ParsedRows(headers=headers)
        for row in reader:
            if None in row:
                raise AppError('A table row has more values than columns', 422, 'MALFORMED_FILE')
            if any(_clean(v) for v in row.values()):
                rows.append(_normalize_row(row))
            if len(rows) > MAX_IMPORT_ROWS:
                raise AppError('Imports are limited to 500 rows; split the file', 413, 'TOO_MANY_ROWS')
        return rows
    except csv.Error as exc:
        raise AppError('The table is malformed', 422, 'MALFORMED_FILE') from exc


def _parse_xlsx(content: bytes) -> ParsedRows:
    """Read the first worksheet without executing workbook content."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            if len(names) > 2000 or len(names) != len(set(names)) or any(name.startswith(("/", '\\')) or '..' in name.replace('\\', '/').split('/') for name in names):
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
            if target.startswith('/xl/'):
                target = target.lstrip('/')
            target = posixpath.normpath(posixpath.join("xl", target)) if not target.startswith("xl/") else target
            if target not in names or not target.startswith("xl/"):
                raise AppError("The XLSX worksheet path is invalid", 422, "MALFORMED_FILE")
            root = ET.fromstring(archive.read(target))
            rows: list[dict[int, str]] = []
            for row in root.findall(".//m:sheetData/m:row", ns):
                values: dict[int, str] = {}
                for cell in row.findall("m:c", ns):
                    if cell.find('m:f', ns) is not None:
                        raise AppError('Spreadsheet formulas are not supported; upload values only', 422, 'UNSAFE_FORMULA')
                    ref = cell.attrib.get('r', f'{chr(ord("A") + len(values))}1')
                    if not re.fullmatch(r'[A-Za-z]{1,3}[1-9][0-9]{0,6}', ref):
                        raise AppError('The workbook contains an invalid cell address', 422, 'MALFORMED_FILE')
                    letters = "".join(char for char in ref if char.isalpha()).upper()
                    index = 0
                    for char in letters:
                        index = index * 26 + ord(char) - ord("A") + 1
                    value = cell.find("m:v", ns)
                    text = "" if value is None else value.text or ""
                    if cell.attrib.get('t') == 'inlineStr':
                        text = ''.join(node.text or '' for node in cell.findall('.//m:t', ns))
                    if cell.attrib.get("t") == "s" and text.isdigit():
                        shared_index = int(text)
                        text = shared[shared_index] if shared_index < len(shared) else ""
                    values[max(index - 1, 0)] = text
                    if index > MAX_COLUMNS:
                        raise AppError('Imports are limited to 20 columns', 413, 'TOO_MANY_COLUMNS')
                rows.append(values)
                if len(rows) > MAX_IMPORT_ROWS + 1:
                    raise AppError('Imports are limited to 500 rows', 413, 'TOO_MANY_ROWS')
    except AppError:
        raise
    except (KeyError, ValueError, ET.ParseError, zipfile.BadZipFile, IndexError) as exc:
        raise AppError("The XLSX workbook is malformed", 422, "MALFORMED_FILE") from exc
    if not rows:
        return ParsedRows()
    width = max((max(row, default=-1) for row in rows), default=-1) + 1
    headers = tuple(_canonical_header(rows[0].get(index, "")) for index in range(width))
    if len(headers) != len(set(headers)) or '' in headers:
        raise AppError('Workbook columns must be unique and nonblank', 422, 'MISSING_REQUIRED_COLUMNS')
    return ParsedRows(
        (_normalize_row({headers[index]: row.get(index, "") for index in range(width)}) for row in rows[1:]),
        headers,
    )


def parse_attendance_file(filename: str, content: bytes, *, values_only: bool = False) -> tuple[str, list[dict[str, str]], bool]:
    """Return ``(strategy, rows, ai_confirmation_required)``."""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix not in ALLOWED_SUFFIXES:
        raise AppError("Unsupported attendance file. Use CSV, XLSX, PDF, or an image.", 422, "UNSUPPORTED_FILE")
    if not content:
        raise AppError("The attendance file is empty", 422, "EMPTY_FILE")
    if len(content) > MAX_IMPORT_BYTES:
        raise AppError('The file exceeds the 10 MB limit', 413, 'FILE_TOO_LARGE')
    if suffix == "csv":
        try:
            return "CSV", _parse_csv(content.decode('utf-8-sig')), False
        except UnicodeDecodeError as exc:
            raise AppError("The CSV file must be UTF-8 encoded", 422, "MALFORMED_FILE") from exc
    if suffix == "xlsx":
        if not content.startswith(b"PK"):
            raise AppError("The XLSX file signature is invalid", 422, "MALFORMED_FILE")
        return "XLSX", _parse_xlsx(content), False
    if suffix == "xls":
        if content.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
            try:
                import xlrd
                if values_only:
                    from xlrd.biffh import (
                        XL_ARRAY,
                        XL_ARRAY2,
                        XL_FORMULA_OPCODES,
                        XL_SHRFMLA,
                    )
                    from xlrd.compdoc import CompDoc
                    compound = CompDoc(content)
                    workbook = compound.get_named_stream('Workbook') or compound.get_named_stream('Book')
                    if not workbook:
                        raise AppError('Missing XLS workbook stream', 422, 'MALFORMED_FILE')
                    offset = 0
                    while offset + 4 <= len(workbook):
                        opcode, size = struct.unpack_from('<HH', workbook, offset)
                        if opcode in {*XL_FORMULA_OPCODES, XL_ARRAY, XL_ARRAY2, XL_SHRFMLA}:
                            raise AppError('Spreadsheet formulas are not supported; upload values only', 422, 'UNSAFE_FORMULA')
                        offset += size + 4
                        if offset > len(workbook):
                            raise AppError('Truncated XLS record', 422, 'MALFORMED_FILE')
                book = xlrd.open_workbook(file_contents=content, on_demand=True)
                sheet = book.sheet_by_index(0)
                if sheet.nrows > MAX_IMPORT_ROWS + 1 or sheet.ncols > MAX_COLUMNS:
                    raise AppError('Workbook exceeds the row/column limits', 413, 'TOO_MANY_ROWS')
                output = io.StringIO()
                writer = csv.writer(output)
                for index in range(sheet.nrows):
                    writer.writerow([str(int(v)) if isinstance(v, float) and v.is_integer() else v for v in sheet.row_values(index)])
                book.release_resources()
                return 'XLS', _parse_csv(output.getvalue()), False
            except AppError:
                raise
            except Exception as exc:
                raise AppError('The legacy workbook could not be read; convert to CSV/XLSX', 422, 'MALFORMED_FILE') from exc
        try:
            decoded = content.decode("utf-8-sig")
            dialect = csv.Sniffer().sniff(decoded[:4096], delimiters=",\t;")
            return 'XLS', _parse_csv(decoded, dialect=dialect), False
        except AppError:
            raise
        except (UnicodeDecodeError, csv.Error) as exc:
            raise AppError("This legacy XLS workbook could not be read deterministically; convert it to XLSX or CSV", 422, "UNSUPPORTED_FILE") from exc
    if suffix == "pdf":
        if not content.startswith(b"%PDF"):
            raise AppError("The PDF file signature is invalid", 422, "MALFORMED_FILE")
        try:
            from app.services.extraction import extract_text
            text = extract_text(content, 'pdf')
        except AppError:
            raise
        except Exception as exc:
            raise AppError("The PDF could not be read safely", 422, "MALFORMED_FILE") from exc
        if not text.strip():
            return "OCR_AI", ParsedRows(), True
        try:
            rows = _parse_csv(text)
            if REQUIRED_IDENTITY_COLUMNS <= set(rows.headers) and SUMMARY_COLUMNS & set(rows.headers):
                return 'PDF_TEXT', rows, False
        except AppError:
            pass
        return 'OCR_AI', ParsedRows(), True
    # OCR/AI is a separately-confirmed integration. No provider is invoked by
    # parsing, and the caller must explicitly confirm before continuing.
    signatures = {'png': content.startswith(b'\x89PNG\r\n\x1a\n'), 'jpg': content.startswith(b'\xff\xd8\xff'),
                  'jpeg': content.startswith(b'\xff\xd8\xff'), 'webp': content.startswith(b'RIFF') and content[8:12] == b'WEBP'}
    if not signatures.get(suffix):
        raise AppError('The image signature does not match its type', 422, 'MALFORMED_FILE')
    try:
        from PIL import Image
        with Image.open(io.BytesIO(content)) as image:
            if image.width * image.height > 20_000_000:
                raise AppError('Image exceeds the 20 megapixel limit', 413, 'IMAGE_TOO_LARGE')
            image.verify()
    except AppError:
        raise
    except Exception as exc:
        raise AppError('The image is malformed or exceeds safe decoding limits', 422, 'MALFORMED_FILE') from exc
    return 'OCR_AI', ParsedRows(), True


def _assert_assigned(current_user: dict, section_id: UUID, permission: str = "attendance.manage") -> dict:
    from app.services.faculty_responsibilities import authorize_section
    return authorize_section(current_user, section_id, permission, teaching_only=True)


def _identity(db, institution_id: str, row: dict[str, str]) -> tuple[dict | None, list[str]]:
    errors: list[str] = []
    register = _clean(row.get("register_number"))
    roll = _clean(row.get("university_roll_number")) or None
    by_register = get_student_by_register_number(db, institution_id, register) if register else None
    by_roll = get_student_by_university_roll_number(db, institution_id, roll) if roll else None
    if by_register and by_roll and by_register["student_id"] != by_roll["student_id"]:
        errors.append("register number and university roll number match different students")
        return None, errors
    student = by_register or by_roll
    if student and ((register and student.get('register_number') and register != student['register_number'])
                    or (roll and student.get('university_roll_number') and roll != student['university_roll_number'])):
        return None, ['provided identifiers conflict with the matched student']
    return student, errors


def match_identity(institution_id: str, row: dict, candidates: list[dict]) -> tuple[dict | None, list[str]]:
    """Exact tenant-local identifiers; ambiguity or disagreement never merges."""
    register, roll = _clean(row.get('register_number')), _clean(row.get('university_roll_number'))
    matches = [s for s in candidates if str(s.get('institution_id')) == institution_id and
               ((register and s.get('register_number') == register) or (roll and s.get('university_roll_number') == roll))]
    unique = {s['student_id']: s for s in matches}
    if len(unique) > 1:
        return None, ['Identifiers match duplicate or conflicting student candidates']
    student = next(iter(unique.values()), None)
    if student and ((register and student.get('register_number') and register != student['register_number']) or
                    (roll and student.get('university_roll_number') and roll != student['university_roll_number'])):
        return None, ['Provided identifiers conflict with the matched student']
    return student, []


def _identity_candidates(db, tenant: str, rows: list[dict]) -> list[dict]:
    candidates = {}
    for column in ('register_number', 'university_roll_number'):
        ids = sorted({_clean(row.get(column)) for row in rows if _clean(row.get(column))})
        for start in range(0, len(ids), 100):
            for student in read_all(db.table('students').select('student_id, institution_id, register_number, university_roll_number, approval_status, is_active, status, program_id, academic_year_id')
                                    .eq('institution_id', tenant).in_(column, ids[start:start + 100]).order('student_id')):
                candidates[student['student_id']] = student
    return list(candidates.values())


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


def validate_rows(current_user: dict, section_id: UUID, semester_id: UUID, rows: list[dict]) -> tuple[dict, list[dict]]:
    context = _assert_assigned(current_user, section_id)
    if len(rows) > MAX_IMPORT_ROWS:
        raise AppError('Imports are limited to 500 rows', 413, 'TOO_MANY_ROWS')
    if str(context["semester_id"]) != str(semester_id):
        raise AppError("The selected semester does not match the assigned section", 422, "ACADEMIC_CONTEXT_MISMATCH")
    db = get_admin_client()
    semester = read_one(db.table("semesters").select("semester_number").eq("semester_id", str(context["semester_id"])).maybe_single())
    first_semester = semester is not None and semester.get("semester_number") == 1
    seen_registers: set[str] = set()
    seen_rolls: set[str] = set()
    reviewed: list[dict] = []
    parsed_rows = rows if isinstance(rows, ParsedRows) else ParsedRows(rows)
    candidates = _identity_candidates(db, str(current_user['institution_id']), parsed_rows)
    existing = read_all(db.table('faculty_attendance_rosters').select('roster_id, register_number, university_roll_number, linked_student_id')
                        .eq('institution_id', str(current_user['institution_id'])).eq('section_id', str(section_id)).order('roster_id'))
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
        if normalized.get('email'):
            from email_validator import EmailNotValidError, validate_email
            try:
                validate_email(normalized['email'], check_deliverability=False)
            except EmailNotValidError:
                errors.append('email is malformed')
        imported_summary = _validate_attendance_fields(normalized, errors)
        student, identity_errors = match_identity(str(current_user['institution_id']), normalized, candidates)
        roster_matches = [r for r in existing if r['register_number'] == normalized.get('register_number') or
                          (roll and r.get('university_roll_number') == normalized.get('university_roll_number'))]
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
        warnings = ['University Roll Number is missing (permitted in first semester)'] if first_semester and not roll else []
        if imported_summary and not normalized.get('status'):
            warnings.append('Summary retained as provenance; no session records will be created')
        reviewed.append({"row_number": number, "raw_data": raw, "normalized_data": normalized, "validation_status": status, "errors": errors, 'warnings': warnings, "student_id": student.get("student_id") if student and not errors else None, "imported_summary": imported_summary})
    summary = {key: sum(1 for row in reviewed if row["validation_status"] == key) for key in ("NEW", "UPDATE", "DUPLICATE", "CONFLICT", "ERROR")}
    summary.update({"total_rows": len(parsed_rows), "valid": summary["NEW"] + summary["UPDATE"], "new_records": summary["NEW"], "updates": summary["UPDATE"], "duplicates": summary["DUPLICATE"], "conflicts": summary["CONFLICT"], "errors": summary["ERROR"]})
    return summary, reviewed


def list_assignments(current_user: dict) -> list[dict]:
    from app.services.phase81_rbac import list_own_faculty_assignments
    rows = list_own_faculty_assignments(current_user)
    return [{**row, "section_id": row["section"]["section_id"], "semester_id": row["section"]["semester_id"], "academic_year_id": row["section"]["academic_year_id"]} for row in rows]


def list_roster(current_user: dict, section_id: UUID, *, limit: int = 100, offset: int = 0, search: str | None = None) -> list[dict]:
    from app.services.faculty_responsibilities import authorize_section
    authorize_section(current_user, section_id, "attendance.read")
    query = get_admin_client().table("faculty_attendance_rosters").select('roster_id, register_number, university_roll_number, student_name, email, roster_status, linked_student_id, reconciliation_state').eq("institution_id", str(current_user["institution_id"])).eq("section_id", str(section_id)).order("register_number").range(offset, offset + limit - 1)
    if search:
        search = re.sub(r'[^\w\s@-]', '', search)
        query = query.or_(f"register_number.ilike.%{search}%,student_name.ilike.%{search}%,email.ilike.%{search}%")
    return read_rows(query)


def create_manual(current_user: dict, section_id: UUID, payload: RosterStudentInput) -> dict:
    context = _assert_assigned(current_user, section_id)
    db = get_admin_client()
    row = payload.model_dump()
    semester = read_one(db.table("semesters").select("semester_number").eq("semester_id", str(context["semester_id"])).maybe_single())
    if semester and semester.get("semester_number") != 1 and not _clean(row.get("university_roll_number")):
        raise AppError("university_roll_number is required except for first semester", 422, "MISSING_REQUIRED_FIELD")
    student, errors = match_identity(str(current_user['institution_id']), row, _identity_candidates(db, str(current_user['institution_id']), [row]))
    if errors:
        raise AppError("; ".join(errors), 422, "IDENTITY_CONFLICT")
    approved = student and student.get('approval_status') == 'approved'
    state = 'UNREGISTERED' if not student else 'PENDING_APPROVAL' if not approved else 'ACTIVE' if student.get('is_active') and student.get('status') == 'active' else 'INACTIVE'
    row.update({"institution_id": str(current_user["institution_id"]), "section_id": str(section_id), "course_offering_id": str(context["course_offering_id"]), "semester_id": str(context["semester_id"]), "created_by": str(current_user["user_id"]), "linked_student_id": student['student_id'] if approved else None, "roster_status": state, 'reconciliation_state': 'LINKED' if approved else 'PENDING' if student else 'NONE'})
    try:
        return read_rows(db.table("faculty_attendance_rosters").insert(row))[0]
    except Exception as exc:
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
    records = read_rows(db.table('faculty_attendance_records').select('record_id').eq('roster_id', str(roster_id)).limit(1))
    if records:
        raise AppError('Roster students with attendance history cannot be deleted', 409, 'ROSTER_HAS_HISTORY')
    marks = read_rows(db.table('test_results').select('test_result_id').eq('roster_id', str(roster_id))
                      .eq('institution_id', str(current_user['institution_id'])).limit(1))
    if marks:
        raise AppError('Roster students with assessment history cannot be deleted', 409, 'ROSTER_HAS_HISTORY')
    try:
        db.table("faculty_attendance_rosters").delete().eq("roster_id", str(roster_id)).eq("institution_id", str(current_user["institution_id"])).execute()
    except Exception as exc:
        # Foreign keys also protect marks written after the initial history check.
        if getattr(exc, 'code', None) == '23503':
            raise AppError('Roster history must be preserved', 409, 'ROSTER_HAS_HISTORY') from exc
        raise
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


def validate_import_filename(filename: str, content_type: str | None = None) -> str:
    """Shared untrusted upload name/MIME checks for academic spreadsheet imports."""
    safe_name = PurePath(filename).name
    if not filename or safe_name != filename or len(filename) > 128 or re.search(r'[\\/:\x00-\x1f\x7f]', filename) or filename in {".", ".."}:
        raise AppError("The attendance filename is unsafe", 422, "UNSAFE_FILENAME")
    allowed_mimes = {'csv': {'text/csv', 'text/plain', 'application/vnd.ms-excel'},
        'xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'},
        'xls': {'application/vnd.ms-excel'}, 'pdf': {'application/pdf'},
        'png': {'image/png'}, 'jpg': {'image/jpeg'}, 'jpeg': {'image/jpeg'}, 'webp': {'image/webp'}}
    suffix = safe_name.rsplit('.', 1)[-1].lower()
    if content_type and content_type.split(';')[0] not in allowed_mimes.get(suffix, set()) | {'application/octet-stream'}:
        raise AppError('The MIME type does not match the filename', 422, 'INVALID_MIME')
    return safe_name


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
        from app.services.faculty_attendance_extraction import extract_attendance_rows
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
    from app.services.faculty_responsibilities import authorize_section
    authorize_section(current_user, UUID(str(item['section_id'])), 'attendance.read')
    rows = read_all(db.table("faculty_attendance_import_rows").select("*").eq("import_id", str(import_id)).order("row_number"))
    return {"import_id": str(import_id), "status": item["status"], "summary": item["summary"], "rows": rows, 'updated_at': item['updated_at']}


def list_imports(current_user: dict, section_id: UUID, *, limit: int = 50, offset: int = 0) -> list[dict]:
    from app.services.faculty_responsibilities import authorize_section
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
    from app.services.faculty_responsibilities import authorize_section
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
    from app.services.faculty_responsibilities import authorize_section
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
