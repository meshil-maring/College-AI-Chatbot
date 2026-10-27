"""Use a real development account and browser; credentials travel only on stdin."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "offerings"))

from account import test_administrator
from transport import development_transport


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--institution-id", required=True, type=UUID)
    parser.add_argument("--resume-prefix", "--sessions-prefix", dest="resume_prefix",
                        help="Resume an E2E run after its base catalogue has been saved")
    args = parser.parse_args()
    log_dir = ROOT / "logs/frontend/browser"
    log_dir.mkdir(parents=True, exist_ok=True)
    retained = {}
    if args.resume_prefix:
        if not re.fullmatch(r"E2E[0-9A-F]{8}", args.resume_prefix):
            parser.error("Session prefix must identify a generated E2E manifest")
        retained = json.loads((log_dir / f"{args.resume_prefix}-records.json").read_text(encoding="utf-8"))
        records = retained["records"]
        if "courses" not in records:
            parser.error("Resumption requires the base academic catalogue to be complete")
        rows = [row for value in records.values() for row in (value if isinstance(value, list) else [value])]
        if any(row.get("institution_id") != str(args.institution_id) for row in rows):
            parser.error("Retained records must all belong to the selected institution")
    with development_transport() as client:
        with test_administrator(client, str(args.institution_id), log_dir) as credentials:
            result = subprocess.run(
                ["node", str(Path(__file__).with_name("journey.mjs"))],
                input=json.dumps({
                    **credentials, "baseURL": "http://127.0.0.1:5180", "logDir": str(log_dir),
                    "records": retained.get("records", {}),
                    "prefix": args.resume_prefix or credentials["prefix"],
                }),
                text=True, encoding="utf-8", errors="replace", timeout=900,
            )
            if result.returncode:
                raise RuntimeError("Real browser journey failed; inspect the browser evidence log")


if __name__ == "__main__":
    main()
