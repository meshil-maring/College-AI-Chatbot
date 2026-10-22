"""Build an institution-pinned academic reset; rollback is the default."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from uuid import UUID

SOURCE = Path(__file__).resolve().parent


def render(institution_id: str, code: str, *, commit: bool = False, expected: dict | None = None) -> str:
    institution_id = str(UUID(institution_id))
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", code):
        raise ValueError("Institution code must use letters, digits, underscores or hyphens")
    if commit and expected is None:
        raise ValueError("A permanent reset requires the reviewed rollback rehearsal report")
    if expected and (expected["institution_id"] != institution_id or expected["institution_code"] != code):
        raise ValueError("Rehearsal target differs from the requested reset")
    parts = ["-- Generated academic-only maintenance; never a deployment migration.", "BEGIN;"]
    for name in ("plan.sql", "preservation.sql", "execute.sql"):
        content = (SOURCE / name).read_text(encoding="utf-8")
        parts.append(content.replace("__INSTITUTION_ID__", institution_id).replace("__INSTITUTION_CODE__", code))
        if name == "preservation.sql" and expected:
            counts = json.dumps(expected["academic_tables"], sort_keys=True).replace("'", "''")
            digest = expected["plan_digest"]
            if not re.fullmatch(r"[a-f0-9]{32}", digest):
                raise ValueError("Invalid rehearsal plan digest")
            parts.append(f"""DO $plan_guard$
BEGIN
    IF (SELECT jsonb_object_agg(name,deleted_rows) FROM reset_counts) IS DISTINCT FROM '{counts}'::jsonb
        OR (SELECT digest FROM reset_plan) IS DISTINCT FROM '{digest}' THEN
        RAISE EXCEPTION 'Academic records changed since reviewed rollback rehearsal';
    END IF;
END;
$plan_guard$;""")
    parts.append("COMMIT;" if commit else "ROLLBACK;")
    return "\n".join(parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--institution-id", required=True)
    parser.add_argument("--code", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--commit", action="store_true", help="Render authorized permanent reset")
    parser.add_argument("--expected-report", type=Path, help="JSON output from the reviewed rollback rehearsal")
    args = parser.parse_args()
    expected = None
    if args.expected_report:
        report = json.loads(args.expected_report.read_text(encoding="utf-8-sig"))
        expected = report["rows"][0]["academic_reset_result"]
    args.output.write_text(render(args.institution_id, args.code, commit=args.commit, expected=expected), encoding="utf-8")
    print(f"Prepared {'COMMIT' if args.commit else 'ROLLBACK'} academic reset: {args.output}")


if __name__ == "__main__":
    main()
