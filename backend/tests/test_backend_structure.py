"""Keep layout regressions visible in the normal automated suite."""

from pathlib import Path
import runpy

import pytest


BACKEND = Path(__file__).resolve().parents[1]
check_structure = runpy.run_path(
    str(BACKEND / "scripts/validation/check_structure.py")
)["check_structure"]


@pytest.fixture
def backend_layout(tmp_path):
    for package in (
        "app", "app/api", "app/services", "app/repositories", "app/schemas",
        "app/api/students", "app/services/students",
    ):
        directory = tmp_path / package
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "__init__.py").write_text('"""Package marker."""\n', encoding="utf-8")
    (tmp_path / "app/services/students/profile.py").write_text(
        "def get_profile():\n    return {}\n", encoding="utf-8",
    )
    (tmp_path / "app/api/students/profile.py").write_text(
        "from app.services.students.profile import get_profile\n", encoding="utf-8",
    )
    return tmp_path


def test_backend_follows_structure_rules():
    assert check_structure(BACKEND) == []


def test_valid_layout_is_checked_without_executing_application(backend_layout):
    (backend_layout / "app/__init__.py").write_text(
        'raise RuntimeError("Structure checks must not import the application")\n',
        encoding="utf-8",
    )
    assert check_structure(backend_layout) == []


@pytest.mark.parametrize(
    ("relative", "content", "expected"),
    [
        ("app/services/profile.py", "", "place implementation in its feature package"),
        ("app/services/other/__init__.py", "", "unknown feature"),
        ("app/api/students/ProfileView.py", "", "Python modules must use lowercase snake_case"),
        ("app/api/students/__init__.py", "from . import profile\n", "docstring-only"),
        ("app/api/students/error.log", "output", "generated output"),
        ("app/api/students/legacy.py", "from app.services.student_profile import get_profile\n", "local import module does not exist"),
        ("tests/test_old_import.py", "import app.repositories.student_profile\n", "local import module does not exist"),
        ("scripts/check_old_import.py", "from app.schemas.student_profile import Profile\n", "local import module does not exist"),
    ],
)
def test_invalid_layout_reports_actionable_error(backend_layout, relative, content, expected):
    path = backend_layout / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    assert any(expected in error for error in check_structure(backend_layout))


def test_missing_package_marker_is_reported(backend_layout):
    (backend_layout / "app/services/students/__init__.py").unlink()
    assert any("require __init__.py" in error for error in check_structure(backend_layout))


def test_generated_caches_are_ignored(backend_layout):
    cache = backend_layout / "app/api/students/__pycache__"
    cache.mkdir()
    (cache / "profile.pyc").write_bytes(b"cached bytecode")
    assert check_structure(backend_layout) == []
