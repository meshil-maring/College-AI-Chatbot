"""Read and pin local replay inputs without importing the application or executing SQL."""
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat

from .policy import HarnessError, require

ROOT = Path(__file__).absolute().parents[3]
PACKAGE = "scripts/validation/academic_setup"
ACADEMIC = (
    "20261023000000_decommission_academic_domain.sql",
    "20261023010000_academic_foundations.sql",
    "20261024000000_academic_structure.sql",
    "20261024010000_academic_sections.sql",
)
LEGACY_FIXTURE = "scripts/validation/academic_decommission/seed.sql"
SCOPE = "supabase/migration_sources/academic_decommission/scope.sql"
SQL_NAMES = (
    "bootstrap", "snapshot", "snapshots/catalog", "snapshots/retained", "snapshots/fixtures",
    "rollback_verify", "retained_verify", "runtime_probe",
    "academic_probes", "security_probes",
    "prerequisite_violation", "prerequisite_restore", "probes/snapshot_differences",
    "probes/helpers", "probes/tenancy_authority", "probes/lifecycle", "probes/audit_atomicity",
    "probes/object_inventory", "probes/catalog_retention", "probes/privilege_roles",
    "probes/decommission_retention", "probes/catalog_properties",
    "concurrency/setup", "concurrency/synchronization", "concurrency/verify", "concurrency/teardown",
)


def local_file(relative):
    require(isinstance(relative, str) and re.fullmatch(r"[A-Za-z0-9_./-]+", relative),
            "Unsafe replay input path")
    parts = relative.split("/")
    require(all(part not in {"", ".", ".."} for part in parts), "Unsafe replay input path")
    require(ROOT.is_absolute() and not str(ROOT).startswith(("\\\\", "//")),
            "A local checkout is required")
    if os.name == "nt":
        import ctypes
        require(ctypes.windll.kernel32.GetDriveTypeW(str(ROOT.anchor)) in (3, 6),
                "A fixed local checkout drive is required")
    current = Path(ROOT.anchor)
    for part in (*ROOT.parts[1:], *parts):
        current = current / part
        metadata = current.lstat()
        require(not stat.S_ISLNK(metadata.st_mode)
                and not getattr(metadata, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024),
                "Linked replay paths are prohibited")
    require(current.is_file(), "Replay input is not a regular file")
    return current


def safe_sql(text):
    require(not re.search(r"(?m)^\s*\\", text), "psql metacommands are prohibited")
    require(not re.search(r"\bCOPY\b[^;]*\bPROGRAM\b", text, re.IGNORECASE),
            "SQL program execution is prohibited")
    return text


@dataclass(frozen=True)
class Artifact:
    path: str
    digest: str
    text: str


@dataclass(frozen=True)
class Plan:
    migrations: tuple[Artifact, ...]
    inputs: dict[str, Artifact]
    retired_tables: tuple[str, ...]
    retired_functions: tuple[str, ...]

    def sql(self, name):
        return self.inputs[f"{PACKAGE}/sql/{name}.sql"].text


def scope_names(text, kind, expected):
    match = re.search(
        rf"INSERT INTO academic_decommission_{kind}\(name\) VALUES(.*?);", text, re.DOTALL,
    )
    require(match is not None, "Missing retirement inventory")
    names = tuple(re.findall(r"\('([a-z][a-z0-9_]*)'\)", match[1]))
    require(len(names) == expected and len(set(names)) == expected,
            "Retirement inventory changed")
    return names


def load_plan():
    manifest = json.loads(local_file(f"{PACKAGE}/manifest.json").read_text(encoding="utf-8"))
    require(manifest.get("execution_authorized") is False, "Preparation-only manifest required")
    entries = [{"path": path, "sha256": digest}
               for path, digest in manifest["migrations"].items()]
    extra = [{"path": path, "sha256": digest}
             for path, digest in manifest["inputs"].items()]
    names = [entry["path"].removeprefix("supabase/migrations/") for entry in entries]
    require(len(names) == 49 and names == sorted(set(names))
            and tuple(names[-4:]) == ACADEMIC
            and all(name < ACADEMIC[0] for name in names[:45]),
            "Expected exactly 45 preceding and four academic migrations")
    directory = local_file("supabase/migrations/" + names[0]).parent
    require(sorted(path.name for path in directory.glob("*.sql")) == names,
            "Migration inventory differs from the pinned 49-file plan")
    required = {LEGACY_FIXTURE, SCOPE,
                *(f"{PACKAGE}/sql/{name}.sql" for name in SQL_NAMES)}
    require(required <= {entry["path"] for entry in extra},
            "Missing fixture, scope or probe input")
    artifacts = {}
    for entry in (*entries, *extra):
        relative, digest = entry["path"], entry["sha256"]
        require(relative not in artifacts and re.fullmatch(r"[a-f0-9]{64}", digest),
                "Duplicate input or invalid fingerprint")
        require(relative.startswith(("supabase/migrations/", "supabase/migration_sources/",
                                     "scripts/maintenance/migrations/", PACKAGE + "/sql/"))
                or relative in {LEGACY_FIXTURE, "scripts/validation/disposable_container.py"},
                "Input is outside the Academic Setup replay contract")
        payload = local_file(relative).read_bytes()
        require(sha256(payload).hexdigest() == digest, "Replay input fingerprint changed")
        text = payload.decode("utf-8")
        if relative.endswith(".sql"):
            safe_sql(text)
        artifacts[relative] = Artifact(relative, digest, text)
    scope = artifacts[SCOPE].text
    return Plan(tuple(artifacts[entry["path"]] for entry in entries), artifacts,
                scope_names(scope, "tables", 39), scope_names(scope, "functions", 71))
