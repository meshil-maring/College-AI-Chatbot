"""Read-only Phase 7.9 infrastructure checks with value-free output.

Run from ``backend/`` so the normal ``.env`` discovery rules apply. The script
does not print endpoints, bucket names, credentials, database rows, or provider
payloads, and it never writes remote data.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

import httpx

from app.config import settings
from app.db.supabase import get_admin_client
from app.services.storage import get_r2_client


def _check(label: str, operation: Callable[[], object]) -> bool:
    try:
        operation()
    except Exception:
        print(f"{label}=FAIL")
        return False
    print(f"{label}=PASS")
    return True


def _openrouter_smoke() -> object:
    response = httpx.post(
        f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openrouter_model,
            "messages": [{"role": "user", "content": "Reply with OK."}],
            "max_tokens": 4,
        },
        timeout=settings.public_generation_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("choices"):
        raise ValueError("provider response contained no choices")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--openrouter-smoke",
        action="store_true",
        help="Make one minimal configured-model request (may incur a small provider cost).",
    )
    args = parser.parse_args()
    database = get_admin_client()
    results = [
        _check(
            "SUPABASE_CONNECTIVITY",
            lambda: (
                database.table("institutions")
                .select("institution_id")
                .limit(1)
                .execute()
            ),
        ),
        _check(
            "PUBLIC_VISIBILITY_COLUMN",
            lambda: (
                database.table("knowledge_sources")
                .select("visibility")
                .limit(1)
                .execute()
            ),
        ),
        _check(
            "PUBLIC_RPC_AVAILABLE",
            lambda: database.rpc(
                "search_public_knowledge_chunks",
                {
                    "query_embedding": [0.0] * settings.embedding_dimensions,
                    "match_count": 1,
                    "filter_institution_id": "00000000-0000-0000-0000-000000000000",
                    "filter_knowledge_source_id": None,
                    "filter_model_name": settings.embedding_model,
                },
            ).execute(),
        ),
        _check(
            "R2_CONNECTIVITY",
            lambda: get_r2_client().list_objects_v2(
                Bucket=settings.r2_bucket,
                MaxKeys=1,
            ),
        ),
    ]
    if args.openrouter_smoke:
        results.append(_check("OPENROUTER_GENERATION", _openrouter_smoke))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
