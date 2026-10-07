import io

import pytest
from PIL import Image
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.faculty_attendance import RosterStudentInput
from app.services.faculty_attendance import parse_attendance_file


def test_csv_is_deterministic_and_does_not_require_ai():
    strategy, rows, needs_ai = parse_attendance_file(
        'attendance.csv', b'register_number,student_name\nR-1,Ada Lovelace\n'
    )
    assert strategy == 'CSV'
    assert rows == [{'register_number': 'R-1', 'student_name': 'Ada Lovelace'}]
    assert needs_ai is False


def test_image_requires_explicit_ai_confirmation():
    output = io.BytesIO()
    Image.new('RGB', (1, 1)).save(output, format='PNG')
    strategy, rows, needs_ai = parse_attendance_file('scan.png', output.getvalue())
    assert (strategy, rows, needs_ai) == ('OCR_AI', [], True)


def test_spoofed_image_is_rejected_before_ocr():
    with pytest.raises(AppError) as error:
        parse_attendance_file('scan.png', b'not-an-image')
    assert error.value.code == 'MALFORMED_FILE'


def test_unsupported_file_is_rejected_before_processing():
    with pytest.raises(AppError) as error:
        parse_attendance_file('attendance.docx', b'')
    assert error.value.code == 'UNSUPPORTED_FILE'


def test_roster_requires_register_number_and_name():
    with pytest.raises(ValidationError):
        RosterStudentInput(register_number='', student_name='')
