"""Verify whole-option enrollment only in an owned, isolated local PostgreSQL."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "academic_workspace"))
from runtime import database, execute, replay, run_file


def main():
    with database() as container:
        replay(container)
        run_file(container, "seed.sql")
        for name in ("seed.sql", "contracts.sql"):
            print(f"CHECK semester_registration/{name}", flush=True)
            print(execute(container, (HERE / name).read_text(encoding="utf-8")), flush=True)
    print("PASS: semester registration SQL verified; owned container removed", flush=True)


if __name__ == "__main__":
    main()
