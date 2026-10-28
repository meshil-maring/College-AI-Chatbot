"""Validate membership SQL against an isolated replay of the deployed baseline."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts/validation"))

from academic_workspace.runtime import database, execute

MIGRATION = "20261028000000_membership_approval_deployment_repair.sql"
EXCLUDED = {
    "20261017000000_b05_invitation_acceptance_security.sql",
    "20261019000000_student_approval_deployment_repair.sql",
}


def main():
    folder = ROOT / "supabase/migrations"
    with database() as container:
        for path in sorted(folder.glob("*.sql")):
            if path.name >= MIGRATION or path.name in EXCLUDED:
                continue
            print(f"REPLAY {path.name}", flush=True)
            execute(container, path.read_text(encoding="utf-8"))
        repair = (folder / MIGRATION).read_text(encoding="utf-8")
        execute(container, repair)
        execute(container, repair)
        print("PASS: repair applied twice to baseline without B05", flush=True)
        for name in ["decisions.sql", "security.sql"]:
            print(execute(container, (Path(__file__).parent / name).read_text(encoding="utf-8")), flush=True)
    print("PASS: approval/rejection contracts validated; owned container removed", flush=True)


if __name__ == "__main__":
    main()
