"""Verify configured auth, storage, retrieval and generation without mocks."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "scripts/validation/academic_workspace/offerings")]
os.environ.update(DEBUG="false", EMAIL_ALLOW_LIVE_IN_DEVELOPMENT="false")

from app.config import settings
from app.services.knowledge.storage import download_file, get_r2_client
from accounts import accounts
from runtime import accepted, application
from transport import development_transport
from workflows import audience, change_audience, chat, login, publication, unpublish


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--institution-id", required=True, type=UUID)
    parser.add_argument("--institution-code", required=True)
    parser.add_argument("--source-id", required=True, type=UUID, help="Existing public hostel resource")
    parser.add_argument("--browser-only", action="store_true", help="Verify browser/auth without creating another resource fixture")
    args = parser.parse_args()
    if not settings.is_local_environment:
        raise RuntimeError("Use development/test settings only")
    tenant, source = str(args.institution_id), str(args.source_id)
    run = uuid4().hex
    evidence = {"run": run, "institution_id": tenant, "status": "running"}
    directory = ROOT / "logs/backend/live-chat-acceptance" / run
    directory.mkdir(parents=True)

    def save():
        (directory / "manifest.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")

    save()
    try:
        with development_transport() as db, application() as (api, origin):
            original = db.table("knowledge_sources").select("*").eq("institution_id", tenant).execute().data
            original_ids = [row["knowledge_source_id"] for row in original]
            documents = db.table("documents").select("document_id").eq("knowledge_source_id", source).execute().data
            versions = db.table("document_versions").select(
                "document_version_id,storage_bucket,storage_object_key,file_checksum,lifecycle_status"
            ).in_("document_id", [row["document_id"] for row in documents]).eq("lifecycle_status", "published").execute().data
            assert versions, "Existing public resource has no published file"
            version = versions[0]
            data = download_file(get_r2_client(), version["storage_bucket"], version["storage_object_key"])
            checksum = "sha256:" + hashlib.sha256(data).hexdigest()
            assert checksum == version["file_checksum"], "Stored file checksum differs"
            evidence["original_file"] = {"document_version_id": version["document_version_id"], "checksum_verified": True}
            print("PASS: existing uploaded document downloads from R2 with matching checksum", flush=True)
            public = accepted(api.post("/api/v1/chat/public", json={
                "institution_code": args.institution_code,
                "message": "Summarize the hostel rules and tell me whether this document is official policy.",
            }))
            assert public["status"] == "success" and public["sources"], "Public answer has no cited evidence"
            assert "sample" in public["answer"].lower() or "draft" in public["answer"].lower()
            assert "[Retrieved chunk" not in json.dumps(public)
            (directory / "public-answer.json").write_text(json.dumps(public, indent=2), encoding="utf-8")
            evidence["public_sources"] = len(public["sources"])
            print("PASS: real public hostel answer preserves draft qualification and source cards", flush=True)
            accepted(api.post("/api/v1/chat/public", json={
                "institution_code": args.institution_code, "message": "What are my marks?",
            }), 401)
            accepted(api.post("/api/v1/chat/public", json={
                "institution_code": args.institution_code, "message": "Show hostel rules", "institution_id": tenant,
            }), 422)
            with accounts(db, tenant, evidence, save) as credentials:
                headers = login(api, credentials)
                try:
                    if not args.browser_only:
                        revision = publication(api, headers, evidence, save)
                        owned_source = revision["knowledge_source_id"]
                        audience(api, headers, owned_source, {"staff"})
                        question = "For the fictional staff workshop, which room should I use and what should I bring?"
                        conversation = chat(api, headers["staff"], tenant, owned_source, question, evidence, "staff", save)
                        chat(api, headers["admin"], tenant, source, "Summarize the hostel rules.", evidence, "admin", save)
                        chat(api, headers["faculty"], tenant, source, "What are the hostel guest rules?", evidence, "faculty", save)
                        revision = change_audience(api, headers, revision, evidence, save)
                        audience(api, headers, owned_source, {"student"})
                        history = accepted(api.get(f"/api/v1/conversations/{conversation}/messages", headers=headers["staff"]))
                        assert not any(item.get("sources") for item in history)
                        assert "Cedar" not in json.dumps(history), "Revoked history leaked old resource content"
                        chat(api, headers["student"], tenant, owned_source, question, evidence, "student", save)
                        print("PASS: republished student audience revokes staff access and old answer content", flush=True)
                    evidence["status"] = "passed"
                    subprocess.run(["node", str(Path(__file__).with_name("browser.mjs"))],
                        input=json.dumps({"accounts": credentials, "backend": origin, "run": run,
                                          "institutionCode": args.institution_code}),
                        text=True, encoding="utf-8", check=True, timeout=900)
                    evidence["browser_verified"] = True
                finally:
                    unpublish(api, headers, evidence, save)
            after = db.table("knowledge_sources").select("*").in_("knowledge_source_id", original_ids).execute().data
            key = lambda row: row["knowledge_source_id"]
            assert sorted(original, key=key) == sorted(after, key=key), "Existing resources changed"
            evidence["existing_resources_unchanged"] = True
            save()
    except Exception as failure:
        evidence.update(status="failed", error_type=type(failure).__name__)
        save()
        raise
    print(f"PASS: configured-service acceptance; evidence logs/backend/live-chat-acceptance/{run}", flush=True)


if __name__ == "__main__":
    main()
