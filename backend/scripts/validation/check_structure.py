"""Check backend layout without importing the application or loading settings."""

from __future__ import annotations

import ast
from pathlib import Path
import re


FEATURES = frozenset(
    {
        "academics",
        "admin",
        "ai",
        "auth",
        "email",
        "invitations",
        "knowledge",
        "platform",
        "students",
    }
)
LAYERS = ("api", "services", "repositories", "schemas")
NAME = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z")


def source_files(directory: Path):
    """Skip generated caches and hidden directories while walking source."""
    for parent, directories, filenames in directory.walk():
        directories[:] = sorted(
            name for name in directories if not name.startswith((".", "__pycache__"))
        )
        for name in sorted(filenames):
            yield parent / name


def check_structure(backend: Path) -> list[str]:
    backend = backend.resolve()
    app = backend / "app"
    errors: list[str] = []

    def report(path: Path, message: str) -> None:
        errors.append(f"{path.relative_to(backend).as_posix()}: {message}")

    for layer in LAYERS:
        directory = app / layer
        if not directory.is_dir():
            report(directory, "missing feature layer")
            continue
        allowed = FEATURES | ({"shared"} if layer == "repositories" else set())
        for child in sorted(directory.iterdir()):
            if child.name.startswith(".") or child.name == "__pycache__":
                continue
            if child.is_dir():
                if child.name not in allowed:
                    report(
                        child,
                        "unknown feature; update STRUCTURE.md and FEATURES together",
                    )
            elif child.name not in {"__init__.py", "README.md"}:
                report(
                    child,
                    "place implementation in its feature package; output belongs in logs/backend",
                )

    for path in source_files(app):
        if path.suffix in {".log", ".pyc", ".pyo"}:
            report(path, "generated output does not belong in application source")
        if path.suffix != ".py":
            continue
        if path.name != "__init__.py" and not NAME.fullmatch(path.stem):
            report(path, "Python modules must use lowercase snake_case")
        for parent in (path.parent, *path.parent.parents):
            if not parent.is_relative_to(app):
                break
            if not (parent / "__init__.py").is_file():
                report(parent, "application packages require __init__.py")
            if parent != app and not NAME.fullmatch(parent.name):
                report(parent, "Python packages must use lowercase snake_case")

    for base in (app, backend / "tests", backend / "scripts"):
        for path in source_files(base):
            if path.suffix != ".py":
                continue
            try:
                tree = ast.parse(
                    path.read_text(encoding="utf-8-sig"), filename=str(path)
                )
            except (SyntaxError, UnicodeError) as exc:
                report(path, f"cannot parse Python source: {exc}")
                continue
            relative = path.relative_to(app) if path.is_relative_to(app) else None
            if relative and relative.parts[0] in LAYERS and path.name == "__init__.py":
                if any(
                    not (
                        isinstance(node, ast.Expr)
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)
                    )
                    for node in tree.body
                ):
                    report(
                        path,
                        "feature-layer package markers must be empty or docstring-only",
                    )
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif (
                    isinstance(node, ast.ImportFrom) and node.level == 0 and node.module
                ):
                    modules = [node.module]
                for module in modules:
                    if module != "app" and not module.startswith("app."):
                        continue
                    target = backend.joinpath(*module.split("."))
                    if (
                        not target.with_suffix(".py").is_file()
                        and not (target / "__init__.py").is_file()
                    ):
                        report(
                            path,
                            f"line {node.lineno}: local import module does not exist: {module}",
                        )

    return sorted(set(errors))


def main() -> int:
    errors = check_structure(Path(__file__).resolve().parents[2])
    if errors:
        print("Backend structure check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Backend structure check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
