"""Add complete fictional academic offerings to an explicitly selected database scope."""

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings
from app.db.supabase import get_admin_client, get_user_by_auth_id
from app.services.academics.academic_setup import get_setup
from app.services.academics.academic_structure import get_structure
from api import administrator_api, create_offering
from catalogue import PROGRAMS, calendar, seed_program
from writer import Writer
from transport import development_transport


def load_context(client, institution_id, actor_id):
    if not settings.is_local_environment:
        raise RuntimeError("Fictional offering data requires the configured development/test environment")
    institution = client.table("institutions").select(
        "institution_id,name,status,is_active"
    ).eq("institution_id", institution_id).single().execute().data
    account = client.table("users").select("auth_user_id,status").eq("id", actor_id).single().execute().data
    if account["status"] != "active":
        raise RuntimeError("Selected administrator is inactive")
    user = asyncio.run(get_user_by_auth_id(account["auth_user_id"], include_permissions=True))
    user["institution_id"] = institution_id
    records = read_catalogues(user)
    if len(get_structure(user).manageable) != 6:
        raise RuntimeError("Selected account cannot manage all academic structure entities")
    return institution, user, records


def read_catalogues(user):
    return {str(key): rows for response in (get_setup(user), get_structure(user))
            for key, rows in response.records.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--institution-id", required=True, type=UUID)
    parser.add_argument("--actor-id", required=True, type=UUID)
    parser.add_argument("--prefix", default="QA26")
    parser.add_argument("--apply", action="store_true", help="Retain created records in the configured database")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Z][A-Z0-9]{1,7}", args.prefix):
        parser.error("Use a 2-8 character uppercase alphanumeric dataset prefix")
    client = get_admin_client()
    tenant, actor = str(args.institution_id), str(args.actor_id)
    institution, user, baseline = load_context(client, tenant, actor)
    print(json.dumps({"institution": institution["name"], "institution_id": tenant,
                      "prefix": args.prefix, "apply": args.apply}), flush=True)
    log_dir = ROOT / "logs/backend"
    log_dir.mkdir(parents=True, exist_ok=True)
    artifact = "manifest" if args.apply else "plan"
    manifest_path = log_dir / f"academic-offerings-{args.prefix}-{artifact}.json"
    baseline_path = log_dir / f"academic-offerings-{args.prefix}-baseline.json"
    if args.apply and not baseline_path.exists():
        baseline_path.write_text(json.dumps({"institution_id": tenant, "records": baseline}, indent=2), encoding="utf-8")
    previous = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    completed = False
    with administrator_api(user) as api_client:
        writer = Writer(client, actor, tenant, deepcopy(baseline), apply=args.apply,
                        http_create=lambda body: create_offering(api_client, body))
        offerings = []
        try:
            terms = calendar(writer, args.prefix)
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = [pool.submit(seed_program, writer, args.prefix, terms, program) for program in PROGRAMS]
                for future in futures:
                    offerings.extend(future.result())
            print(json.dumps(writer.summary()), flush=True)
            if args.apply:
                from verification import verify
                verify(client, api_client, user, baseline, offerings, writer)
            else:
                print(f"DRY RUN: {len(offerings)} offerings planned; no database records written", flush=True)
            completed = True
        finally:
            operations = {item["record_id"]: item for item in previous.get("operations", [])
                          if previous.get("applied") and previous.get("institution", {}).get("institution_id") == tenant}
            operations.update({item["record_id"]: item for item in writer.operations})
            manifest_path.write_text(json.dumps({
                "institution": institution, "prefix": args.prefix, "applied": args.apply,
                "completed": completed, **writer.summary(), "operations": list(operations.values()), "offerings": offerings,
                "referenced_records": writer.touched,
            }, indent=2), encoding="utf-8")
    print(f"MANIFEST {manifest_path}", flush=True)


if __name__ == "__main__":
    with development_transport():
        main()
