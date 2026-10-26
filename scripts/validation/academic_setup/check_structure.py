"""Non-mutating size/layout validation for this harness and its dedicated tests."""
import ast
from pathlib import Path


def check_structure(root=None):
    root = root or Path(__file__).parent
    errors = []
    for directory, folders, files in root.walk():
        folders[:] = [name for name in folders if name != '__pycache__' and not name.startswith('.')]
        files = [name for name in files if not name.endswith(('.pyc', '.pyo'))]
        if len(files) > 15:
            errors.append(f'{directory.relative_to(root)}: {len(files)} direct files exceeds 15')
        for name in files:
            path = directory/name
            text = path.read_text(encoding='utf-8-sig')
            if len(text.splitlines()) > 250:
                errors.append(f'{path.relative_to(root)}: exceeds 250 physical lines')
            if path.suffix == '.py':
                try:
                    ast.parse(text)
                except SyntaxError:
                    errors.append(f'{path.relative_to(root)}: invalid Python syntax')
    return errors


def main():
    errors = check_structure()
    print('\n'.join(errors) if errors else 'Academic Setup structure check passed (15 files / 250 lines).')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
