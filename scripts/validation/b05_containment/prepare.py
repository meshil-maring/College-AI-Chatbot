"""B05 preparation only: read pinned local files and print the replay contract.

No Docker, subprocesses, SQL execution, environment loading or database clients.
This module is not an executor and accepts no execution or target flags.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path

PACKAGE = Path(__file__).parent  # Lexical only: never resolve an unchecked path.
REPOSITORY = PACKAGE.parents[2]
PACKAGE_RELATIVE = "scripts/validation/b05_containment"
PURPOSE = "b05-containment-validation"
B05 = "20261017000000_b05_invitation_acceptance_security.sql"
SUCCESSOR_SOURCE = "docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_POST_B05_SUCCESSOR_DRAFT.sql"
SUCCESSOR_COPY = PACKAGE_RELATIVE + "/containment_successor.validation.sql"
PINNED_INPUTS = {
    "docs/reviews/student_enrollment_final_2026-10-11/SECURITY_CONTAINMENT_MIGRATION_CANDIDATE.sql",
    SUCCESSOR_SOURCE, "scripts/validation/disposable_container.py",
    *(PACKAGE_RELATIVE + "/" + name for name in (
        "bootstrap.sql", "containment_successor.validation.sql", "fixtures_pre_b05.sql",
        "fixtures_post_b05.sql", "prepare.py", "README.md", "runner_contract.json",
        "test_matrix.md", "test_preparation_safety.py",
    )),
}
DEVICE_NAME = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", re.IGNORECASE)


def relative_parts(relative: str) -> tuple[str, ...]:
    """Reject external/ambiguous syntax without touching any filesystem."""
    if not isinstance(relative, str) or not relative:
        raise ValueError("Expected a nonempty repository-relative path")
    parts = tuple(relative.split("/"))
    if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part)
           or part in (".", "..") or part.endswith(".")
           or DEVICE_NAME.fullmatch(part) for part in parts):
        raise ValueError(f"Unsafe repository-relative path: {relative!r}")
    return parts


def require_local_drive(root: Path) -> None:
    """Use only a Windows fixed/RAM disk; reject UNC/mapped drives before lstat."""
    if (os.name != "nt" or not root.is_absolute()
            or not re.fullmatch(r"[A-Za-z]:", root.drive)
            or any(part in (".", "..") or ":" in part
                   or part.rstrip(" .") != part or DEVICE_NAME.fullmatch(part)
                   for part in root.parts[1:])):
        raise ValueError("Preparation requires an absolute local Windows repository")
    # Local volume classification only. No target lookup, resolution or client I/O.
    import ctypes
    get_drive_type = ctypes.WinDLL("kernel32", use_last_error=True).GetDriveTypeW
    get_drive_type.argtypes = [ctypes.c_wchar_p]
    get_drive_type.restype = ctypes.c_uint
    if get_drive_type(root.anchor) not in (3, 6):  # DRIVE_FIXED, DRIVE_RAMDISK
        raise ValueError("Remote, unknown and removable repository drives are prohibited")


def checked_path(relative: str, *, directory: bool = False) -> Path:
    parts = relative_parts(relative)  # Must precede even repository metadata access.
    require_local_drive(REPOSITORY)
    path = Path(REPOSITORY.anchor)
    components = (*REPOSITORY.parts[1:], *parts)
    for position in range(len(components) + 1):
        if position:
            path = path / components[position - 1]
        info = path.lstat()  # Do not follow this component before inspecting it.
        if (stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError(f"Reparse points and symbolic links are prohibited: {path}")
        want_directory = position < len(components) or directory
        if not (stat.S_ISDIR(info.st_mode) if want_directory else stat.S_ISREG(info.st_mode)):
            raise ValueError(f"Unexpected repository path type: {path}")
    return path


def local_file(relative: str) -> Path:
    return checked_path(relative)


def preparation_plan() -> dict:
    manifest = json.loads(local_file(PACKAGE_RELATIVE + "/migration_manifest.json").read_text(encoding="utf-8"))
    contract = json.loads(local_file(PACKAGE_RELATIVE + "/runner_contract.json").read_text(encoding="utf-8"))
    if (contract["purpose"] != PURPOSE or contract["execution_authorized"] is not False
            or contract["runner_mode"] != "file_only_preparation"
            or contract["generic_purpose_registration"] is not False
            or contract["runtime_adapter"] is not None):
        raise ValueError("Only the dedicated preparation contract is supported")
    pinned_paths = [entry["path"] for entry in manifest["pinned_inputs"]]
    if (len(pinned_paths) != len(PINNED_INPUTS) or set(pinned_paths) != PINNED_INPUTS
            or manifest["successor_source"] != SUCCESSOR_SOURCE
            or manifest["successor_validation_copy"] != SUCCESSOR_COPY):
        raise ValueError("Expected the exact reviewed package/source input set")
    migrations = manifest["migrations"]
    expected = [entry["filename"] for entry in migrations]
    actual = sorted(p.name for p in checked_path("supabase/migrations", directory=True).glob("*.sql"))
    if len(migrations) != 40 or expected != actual or expected[-1] != B05:
        raise ValueError("Expected the exact ordered 40-file B05 source chain")
    versions = [entry["version"] for entry in migrations]
    if len(set(versions)) != 40 or versions != sorted(versions):
        raise ValueError("Duplicate or unordered migration versions")
    for position, entry in enumerate(migrations, 1):
        if (entry["order"] != position or entry["filename"][:14] != entry["version"]
                or entry["migration_name"] != entry["filename"][15:-4]
                or entry["path"] != "supabase/migrations/" + entry["filename"]):
            raise ValueError("Migration ordering/identity mismatch")
    for entry in migrations + manifest["pinned_inputs"]:
        raw = local_file(entry["path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["sha256"] or len(raw) != entry["bytes"]:
            raise ValueError(f"Pinned bytes changed: {entry['path']}")
    successor = local_file(manifest["successor_source"]).read_bytes()
    if successor != local_file(manifest["successor_validation_copy"]).read_bytes():
        raise ValueError("Stopped successor copy must match its source byte for byte")
    for marker in (b"DO $review_stop$", b"DO $dependency_stop$", b"ROLLBACK;"):
        if marker not in successor:
            raise ValueError("A successor review stop or rollback is missing")
    return {
        "purpose": PURPOSE,
        "status": "PREPARED_ONLY_NOT_RUN",
        "execution_authorized": False,
        "migration_count": 40,
        "migration_order": expected,
        "lanes": manifest["intended_lanes"],
        "matrix": "scripts/validation/b05_containment/test_matrix.md",
        "runtime_adapter": None,
        "successor_body": "BLOCKED: both stops and final rollback retained",
        "availability": "UNVERIFIED: no Docker/database/extension/provider inspection performed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()  # No purpose, execute, target or connection options.
    print(json.dumps(preparation_plan(), indent=2))


if __name__ == "__main__":
    main()
