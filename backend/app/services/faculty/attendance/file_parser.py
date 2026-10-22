"""Safe deterministic file parsing before any confirmed OCR extraction."""

import csv
import io
import re
import struct
from pathlib import PurePath

from app.core.errors import AppError
from app.services.faculty.attendance.row_format import (
    ALLOWED_SUFFIXES, MAX_COLUMNS, MAX_IMPORT_BYTES, MAX_IMPORT_ROWS,
    MAX_UNPACKED_XLSX_BYTES, REQUIRED_IDENTITY_COLUMNS, SUMMARY_COLUMNS,
    ParsedRows, _parse_csv,
)
from app.services.faculty.attendance.workbook import _parse_xlsx

def parse_attendance_file(filename: str, content: bytes, *, values_only: bool = False, max_unpacked_bytes=MAX_UNPACKED_XLSX_BYTES) -> tuple[str, list[dict[str, str]], bool]:
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
        return "XLSX", _parse_xlsx(content, max_unpacked_bytes=max_unpacked_bytes), False
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
            from app.services.knowledge.extraction import extract_text
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


