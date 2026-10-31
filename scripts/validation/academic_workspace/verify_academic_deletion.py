"""Validate academic deletion only in a run-owned, isolated PostgreSQL."""

from pathlib import Path

from runtime import database, execute, replay, run_file


ROOT = Path(__file__).resolve().parents[3]


def main():
    with database() as container:
        replay(container)
        run_file(container, "seed.sql")
        for name in ("contracts.sql", "program_contracts.sql", "program_integrity.sql",
                     "calendar_contracts.sql", "section_contracts.sql", "calendar_section_integrity.sql"):
            sql = ROOT / "backend/tests/academics/deletion" / name
            execute(container, sql.read_text(encoding="utf-8"))
        print("PASS: deletion, inactive dependencies, authorization, isolation and audit", flush=True)
    print("PASS: run-owned validation database removed", flush=True)


if __name__ == "__main__":
    main()
