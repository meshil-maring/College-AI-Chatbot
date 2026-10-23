from .support import (
    CHUNK_FAQ_A1,
    CHUNK_FAQ_B1,
    CHUNK_PRIVATE_A1,
    INST_A1,
    INST_A2,
    INST_B1,
    KS_FAQ_A1,
    KS_FAQ_B1,
    KS_PRIVATE_A1,
    ORG_A,
    ORG_B,
    RUN_FAQ_A1,
    RUN_FAQ_B1,
    RUN_PRIVATE_A1,
    uuid4,
)


def _org_row(org_id=ORG_A, status="active"):
    return {
        "organization_id": org_id,
        "name": "Acme Org" if org_id == ORG_A else "Beta Org",
        "organization_code": "ACME" if org_id == ORG_A else "BETA",
        "official_email": "info@acme.example.com",
        "contact_information": "contact@acme.example.com",
        "status": status,
        "join_code": None,
        "created_at": "2026-09-19T00:00:00Z",
        "updated_at": "2026-09-19T00:00:00Z",
    }


def _inst_row(inst_id=INST_A1, org_id=ORG_A, status="active"):
    codes = {INST_A1: "IMPHAL", INST_A2: "CHURACHANDPUR", INST_B1: "BETACOLLEGE"}
    return {
        "institution_id": inst_id,
        "organization_id": org_id,
        "name": "Campus",
        "code": codes[inst_id],
        "email": None,
        "address": None,
        "city": None,
        "state": None,
        "country": None,
        "status": status,
        "is_active": status == "active",
        "created_at": "2026-09-19T00:00:00Z",
        "updated_at": "2026-09-19T00:00:00Z",
    }


def _ks_row(ks_id, inst_id, source_type="faq", lifecycle="published"):
    return {
        "knowledge_source_id": ks_id,
        "institution_id": inst_id,
        "source_type": source_type,
        "title": f"Source {source_type}",
        "description": None,
        "authority_level": "official",
        "visibility": "public" if source_type == "faq" else "restricted",
        "lifecycle_status": lifecycle,
        "effective_from": None,
        "effective_until": None,
        "created_at": "2026-09-19T00:00:00Z",
        "updated_at": "2026-09-19T00:00:00Z",
    }


def _run_row(run_id, ks_row):
    return {
        "processing_run_id": run_id,
        "status": "ready",
        "embedding_status": "embedded",
        "completed_at": "2026-09-19T00:00:00Z",
        "document_versions": {
            "document_version_id": str(uuid4()),
            "document_id": str(uuid4()),
            "lifecycle_status": "published",
            "effective_from": None,
            "effective_until": None,
            "documents": {
                "document_id": str(uuid4()),
                "knowledge_source_id": ks_row["knowledge_source_id"],
                "knowledge_sources": ks_row,
            },
        },
    }


def _base_state():
    """Org A {Inst A1, Inst A2}, Org B {Inst B1} — all ACTIVE."""
    faq_a = _ks_row(KS_FAQ_A1, INST_A1, "faq")
    private_a = _ks_row(KS_PRIVATE_A1, INST_A1, "private")
    faq_b = _ks_row(KS_FAQ_B1, INST_B1, "faq")
    run_a = _run_row(RUN_FAQ_A1, faq_a)
    run_private = _run_row(RUN_PRIVATE_A1, private_a)
    run_b = _run_row(RUN_FAQ_B1, faq_b)
    return {
        "organizations": [
            _org_row(ORG_A, "active"),
            _org_row(ORG_B, "active"),
        ],
        "institutions": [
            _inst_row(INST_A1, ORG_A, "active"),
            _inst_row(INST_A2, ORG_A, "active"),
            _inst_row(INST_B1, ORG_B, "active"),
        ],
        "knowledge_sources": [
            faq_a,
            private_a,
            faq_b,
        ],
        "document_processing_runs": [
            run_a,
            run_private,
            run_b,
        ],
        "knowledge_chunks": [
            {
                "chunk_id": CHUNK_FAQ_A1,
                "content_text": "Org A public fact",
                "chunk_sequence": 1,
                "processing_run_id": RUN_FAQ_A1,
                "document_processing_runs": run_a,
            },
            {
                "chunk_id": CHUNK_PRIVATE_A1,
                "content_text": "CONFIDENTIAL private doc",
                "chunk_sequence": 1,
                "processing_run_id": RUN_PRIVATE_A1,
                "document_processing_runs": run_private,
            },
            {
                "chunk_id": CHUNK_FAQ_B1,
                "content_text": "Org B secret fact",
                "chunk_sequence": 1,
                "processing_run_id": RUN_FAQ_B1,
                "document_processing_runs": run_b,
            },
        ],
    }
