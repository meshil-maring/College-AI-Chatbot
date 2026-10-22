"""Values-only XLSX decoding with bounded paths, rows and expansion."""

import io
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile

from app.core.errors import AppError
from app.services.faculty.attendance.row_format import (
    MAX_COLUMNS, MAX_IMPORT_ROWS, MAX_UNPACKED_XLSX_BYTES,
    ParsedRows, _canonical_header, _normalize_row,
)

def _parse_xlsx(content: bytes, *, max_unpacked_bytes=MAX_UNPACKED_XLSX_BYTES) -> ParsedRows:
    """Read the first worksheet without executing workbook content."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
            if len(names) > 2000 or len(names) != len(set(names)) or any(name.startswith(("/", '\\')) or '..' in name.replace('\\', '/').split('/') for name in names):
                raise AppError("The workbook contains an unsafe internal path", 422, "MALFORMED_FILE")
            if sum(info.file_size for info in archive.infolist()) > max_unpacked_bytes:
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


