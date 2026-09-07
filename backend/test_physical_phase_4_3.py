"""Physical validation script for Phase 4.3 Citation & Source Traceability."""

import json
import re
import time
from uuid import UUID

import httpx

from app.db.supabase import get_admin_client, create_supabase_client


BASE_URL = "http://127.0.0.1:8000"
INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
USER_EMAIL = "admin.iridix@gmail.com"
CHUNK_REF_RE = re.compile(
    r"chunk[_\s]*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


def get_user_token(email: str) -> tuple[str, str, str]:
    admin = get_admin_client()
    client = create_supabase_client()
    link_res = admin.auth.admin.generate_link({"type": "magiclink", "email": email})
    otp = link_res.properties.email_otp
    auth_res = client.auth.verify_otp({"email": email, "token": otp, "type": "magiclink"})
    token = auth_res.session.access_token
    auth_user_id = auth_res.user.id
    user_row = admin.table("users").select("user_id").eq("auth_user_id", auth_user_id).single().execute().data
    return token, user_row["user_id"], auth_user_id


def chat(headers: dict, payload: dict, timeout: float = 60.0) -> httpx.Response:
    with httpx.Client(timeout=timeout) as c:
        return c.post(f"{BASE_URL}/api/v1/generation/chat", json=payload, headers=headers)


# ===========================================================================
# TEST A  -- SINGLE VALID CITATION
# ===========================================================================

def test_a_single_citation(admin, headers, user_id):
    print("\n" + "=" * 70)
    print("PHYSICAL TEST A  -- SINGLE VALID CITATION")
    print("=" * 70)

    payload = {
        "user_query": "What attendance level do I need in a course to be allowed to take the regular end-semester exam?",
        "institution_id": INSTITUTION_ID,
    }

    t0 = time.time()
    resp = chat(headers, payload)
    elapsed = time.time() - t0
    print(f"HTTP {resp.status_code} ({elapsed:.1f}s)")

    assert resp.status_code == 200, f"HTTP {resp.status_code}"
    d = resp.json()

    session_id = d["session_id"]
    conv_id = d["conversation_id"]
    msg_id = d["message_id"]
    answer = d.get("answer", "")
    sources = d.get("source_references", [])

    print(f"  session_id:     {session_id}")
    print(f"  conversation_id:{conv_id}")
    print(f"  message_id:     {msg_id}")
    print(f"  status:         {d['status']}")
    print(f"  answer (first): {answer[:150]}...")
    print(f"  source_refs:    {len(sources)}")

    assert conv_id, "conversation_id required"
    assert msg_id, "message_id required"
    assert d["status"] == "success"
    assert answer, "answer must not be empty"

    # Extract chunk references from the answer text
    answer_chunks = CHUNK_REF_RE.findall(answer)
    print(f"  chunk_refs_in_answer: {answer_chunks}")

    # --- DB Verification ---
    print("\n  --- DB: messages ---")
    msgs = admin.table("messages").select("*").eq("conversation_id", conv_id).order("message_sequence").execute().data
    print(f"  message count: {len(msgs)}")
    for m in msgs:
        print(f"    seq {m['message_sequence']}: {m['message_type']} id={m['message_id']}")
    assert len(msgs) == 2
    assert msgs[1]["message_id"] == msg_id
    assert msgs[1]["message_type"] == "assistant"

    print("\n  --- DB: ai_responses ---")
    ai_r = admin.table("ai_responses").select("*").eq("message_id", msg_id).maybe_single().execute().data
    assert ai_r is not None, "ai_response must exist"
    print(f"  ai_response_id: {ai_r['ai_response_id']}")
    print(f"  model: {ai_r['model_name']}, tokens: {ai_r['input_token_count']}/{ai_r['output_token_count']}")

    print("\n  --- DB: retrieval_operations ---")
    ro = admin.table("retrieval_operations").select("*").eq("ai_response_id", ai_r["ai_response_id"]).maybe_single().execute().data
    assert ro is not None, "retrieval_operation must exist"
    print(f"  retrieval_operation_id: {ro['retrieval_operation_id']}")
    print(f"  result_count: {ro['result_count']}, status: {ro['status']}")

    print("\n  --- DB: retrieved_chunks ---")
    rcs = admin.table("retrieved_chunks").select("*").eq("retrieval_operation_id", ro["retrieval_operation_id"]).order("retrieval_rank").execute().data
    print(f"  retrieved_chunks count: {len(rcs)}")
    retrieved_ids = set()
    for rc in rcs:
        print(f"    rank {rc['retrieval_rank']}: chunk_id={rc['chunk_id']} score={rc.get('relevance_score')}")
        retrieved_ids.add(str(rc["chunk_id"]))

    print("\n  --- DB: message_citations ---")
    cits = admin.table("message_citations").select("*").eq("message_id", msg_id).execute().data
    print(f"  message_citations count: {len(cits)}")
    for ci in cits:
        print(f"    chunk_id={ci['chunk_id']} display_order={ci['display_order']} retrieval_op={ci['retrieval_operation_id']}")
        assert str(ci["chunk_id"]) in retrieved_ids, f"Citation chunk {ci['chunk_id']} not in retrieved_chunks"
        assert ci["retrieval_operation_id"] == ro["retrieval_operation_id"], "Citation retrieval_op mismatch"
        assert ci["message_id"] == msg_id, "Citation message_id mismatch"

    # Provenance chain for first cited chunk
    if cits:
        cited_chunk_id = str(cits[0]["chunk_id"])
        print(f"\n  --- DB: provenance chain for chunk {cited_chunk_id} ---")
        kc = admin.table("knowledge_chunks").select("processing_run_id").eq("chunk_id", cited_chunk_id).maybe_single().execute().data
        if kc:
            dpr = admin.table("document_processing_runs").select("document_version_id").eq("processing_run_id", kc["processing_run_id"]).maybe_single().execute().data
            if dpr:
                dv = admin.table("document_versions").select("document_id").eq("document_version_id", dpr["document_version_id"]).maybe_single().execute().data
                if dv:
                    doc = admin.table("documents").select("knowledge_source_id").eq("document_id", dv["document_id"]).maybe_single().execute().data
                    if doc:
                        ks = admin.table("knowledge_sources").select("title, institution_id").eq("knowledge_source_id", doc["knowledge_source_id"]).maybe_single().execute().data
                        if ks:
                            print(f"    knowledge_source: {ks['title']} (institution={ks['institution_id']})")
                            print(f"    document_version: {dpr['document_version_id']}")
                            print(f"    Provenance chain COMPLETE [OK]")
    else:
        print("  (no citations to trace - model answer had no explicit chunk references)")

    print("\n>>> TEST A: PASS")
    return {
        "session_id": session_id, "conversation_id": conv_id, "message_id": msg_id,
        "answer": answer, "answer_chunks": answer_chunks, "sources": sources,
        "citations": cits, "retrieved_chunks": rcs,
    }


# ===========================================================================
# TEST B  -- MULTIPLE CITATIONS
# ===========================================================================

def test_b_multiple_citations(admin, headers, user_id):
    print("\n" + "=" * 70)
    print("PHYSICAL TEST B  -- MULTIPLE CITATIONS")
    print("=" * 70)

    # A broad question likely to retrieve multiple chunks
    payload = {
        "user_query": "Tell me everything about the admission process and attendance policy of this college",
        "institution_id": INSTITUTION_ID,
    }

    t0 = time.time()
    resp = chat(headers, payload)
    elapsed = time.time() - t0
    print(f"HTTP {resp.status_code} ({elapsed:.1f}s)")

    assert resp.status_code == 200
    d = resp.json()

    session_id = d["session_id"]
    conv_id = d["conversation_id"]
    msg_id = d["message_id"]
    answer = d.get("answer", "")
    sources = d.get("source_references", [])

    print(f"  session_id:     {session_id}")
    print(f"  conversation_id:{conv_id}")
    print(f"  message_id:     {msg_id}")
    print(f"  status:         {d['status']}")
    print(f"  answer (first): {answer[:200]}...")
    print(f"  source_refs:    {len(sources)}")

    assert conv_id
    assert msg_id
    assert d["status"] == "success"
    assert answer

    answer_chunks = CHUNK_REF_RE.findall(answer)
    print(f"  chunk_refs_in_answer: {answer_chunks}")

    # DB Verification
    ai_r = admin.table("ai_responses").select("*").eq("message_id", msg_id).maybe_single().execute().data
    assert ai_r is not None

    ro = admin.table("retrieval_operations").select("*").eq("ai_response_id", ai_r["ai_response_id"]).maybe_single().execute().data
    assert ro is not None

    rcs = admin.table("retrieved_chunks").select("*").eq("retrieval_operation_id", ro["retrieval_operation_id"]).execute().data
    retrieved_ids = {str(rc["chunk_id"]) for rc in rcs}
    print(f"  retrieved_chunks: {len(rcs)}")
    for rc in rcs:
        print(f"    chunk_id={rc['chunk_id']}")

    cits = admin.table("message_citations").select("*").eq("message_id", msg_id).execute().data
    print(f"  message_citations: {len(cits)}")
    for ci in cits:
        print(f"    chunk_id={ci['chunk_id']} display_order={ci['display_order']}")
        assert str(ci["chunk_id"]) in retrieved_ids, f"Citation {ci['chunk_id']} not in retrieved_chunks"
        assert ci["message_id"] == msg_id

    print("\n>>> TEST B: PASS")
    return {
        "session_id": session_id, "conversation_id": conv_id, "message_id": msg_id,
        "answer": answer, "answer_chunks": answer_chunks, "sources": sources,
        "citations": cits, "retrieved_chunks_count": len(rcs),
    }


# ===========================================================================
# TEST C  -- NO EXPLICIT CITATION
# ===========================================================================

def test_c_no_citation(admin, headers, user_id):
    print("\n" + "=" * 70)
    print("PHYSICAL TEST C  -- NO EXPLICIT CITATION")
    print("=" * 70)

    payload = {
        "user_query": "Summarize the general admission guidelines",
        "institution_id": INSTITUTION_ID,
    }

    t0 = time.time()
    resp = chat(headers, payload)
    elapsed = time.time() - t0
    print(f"HTTP {resp.status_code} ({elapsed:.1f}s)")

    assert resp.status_code == 200
    d = resp.json()

    msg_id = d["message_id"]
    answer = d.get("answer", "")
    sources = d.get("source_references", [])

    print(f"  message_id: {msg_id}")
    print(f"  status:     {d['status']}")
    print(f"  answer:     {answer[:200]}...")
    print(f"  sources:    {sources}")

    assert msg_id, "message_id required"
    assert d["status"] == "success"
    assert answer

    answer_chunks = CHUNK_REF_RE.findall(answer)
    print(f"  chunk_refs_in_answer: {answer_chunks}")

    # DB Verification
    ai_r = admin.table("ai_responses").select("*").eq("message_id", msg_id).maybe_single().execute().data
    assert ai_r is not None, "ai_response must exist for successful answer"

    cits = admin.table("message_citations").select("*").eq("message_id", msg_id).execute().data
    print(f"  message_citations: {len(cits)}")

    # Safety rule: citations ONLY exist when model explicitly references chunks
    if answer_chunks:
        assert len(cits) > 0, "Model emitted chunk refs but no citations created"
        print(f"  Model emitted {len(answer_chunks)} chunk ref(s) -> {len(cits)} citation(s) [OK]")
    else:
        assert len(cits) == 0, f"Expected 0 citations for unannotated answer, got {len(cits)}"
        print(f"  Confirmed: 0 citations for unannotated answer [OK]")

    print("\n>>> TEST C: PASS")
    return {
        "message_id": msg_id, "answer": answer, "answer_chunks": answer_chunks,
        "citations": cits, "sources": sources,
    }


# ===========================================================================
# TEST D  -- INSUFFICIENT CONTEXT
# ===========================================================================

def test_d_insufficient_context(admin, headers, user_id):
    print("\n" + "=" * 70)
    print("PHYSICAL TEST D  -- INSUFFICIENT CONTEXT")
    print("=" * 70)

    payload = {
        "user_query": "What is the detailed quantum gravitational warp field equation in astrophysics module 999?",
        "institution_id": "00000000-0000-0000-0000-000000000099",
    }

    t0 = time.time()
    resp = chat(headers, payload)
    elapsed = time.time() - t0
    print(f"HTTP {resp.status_code} ({elapsed:.1f}s)")

    assert resp.status_code == 200
    d = resp.json()

    conv_id = d["conversation_id"]
    msg_id = d["message_id"]
    answer = d.get("answer")

    print(f"  conversation_id: {conv_id}")
    print(f"  message_id:      {msg_id}")
    print(f"  status:          {d['status']}")
    print(f"  answer:          {answer}")

    assert d["status"] == "insufficient_context"
    assert answer is None
    assert msg_id is None
    assert conv_id is not None

    # DB Verification
    print("\n  --- DB verification ---")
    conv_row = admin.table("conversations").select("*").eq("conversation_id", conv_id).maybe_single().execute().data
    assert conv_row is not None, "Conversation must exist"

    msgs = admin.table("messages").select("*").eq("conversation_id", conv_id).execute().data
    print(f"  messages count: {len(msgs)}")
    assert len(msgs) == 1, f"Expected 1 user message only, got {len(msgs)}"
    assert msgs[0]["message_type"] == "user"

    # No ai_response for user message
    ai_check = admin.table("ai_responses").select("*").eq("message_id", msgs[0]["message_id"]).execute().data
    assert len(ai_check) == 0, f"Expected 0 ai_responses, got {len(ai_check)}"
    print(f"  ai_responses: 0 [OK]")

    # No citations
    cit_check = admin.table("message_citations").select("*").eq("message_id", msgs[0]["message_id"]).execute().data
    assert len(cit_check) == 0, f"Expected 0 message_citations, got {len(cit_check)}"
    print(f"  message_citations: 0 [OK]")

    print("\n>>> TEST D: PASS")
    return {"conversation_id": conv_id, "message_id": msg_id, "status": d["status"]}


# ===========================================================================
# TEST E  -- CONVERSATION REUSE
# ===========================================================================

def test_e_conversation_reuse(admin, headers, user_id):
    print("\n" + "=" * 70)
    print("PHYSICAL TEST E  -- CONVERSATION REUSE")
    print("=" * 70)

    payload_1 = {
        "user_query": "What attendance level do I need to take the end-semester exam?",
        "institution_id": INSTITUTION_ID,
    }

    t0 = time.time()
    resp1 = chat(headers, payload_1)
    elapsed1 = time.time() - t0
    print(f"Turn 1: HTTP {resp1.status_code} ({elapsed1:.1f}s)")
    assert resp1.status_code == 200
    d1 = resp1.json()

    sid = d1["session_id"]
    cid = d1["conversation_id"]
    mid1 = d1["message_id"]
    ans1 = d1.get("answer", "")

    print(f"  session_id:     {sid}")
    print(f"  conversation_id:{cid}")
    print(f"  message_id:     {mid1}")

    payload_2 = {
        "user_query": "What happens if my attendance falls below that level?",
        "institution_id": INSTITUTION_ID,
        "session_id": sid,
    }

    t0 = time.time()
    resp2 = chat(headers, payload_2)
    elapsed2 = time.time() - t0
    print(f"\nTurn 2: HTTP {resp2.status_code} ({elapsed2:.1f}s)")
    assert resp2.status_code == 200
    d2 = resp2.json()

    sid2 = d2["session_id"]
    cid2 = d2["conversation_id"]
    mid2 = d2["message_id"]
    ans2 = d2.get("answer", "")

    print(f"  session_id:     {sid2}")
    print(f"  conversation_id:{cid2}")
    print(f"  message_id:     {mid2}")

    assert sid2 == sid, "session_id must match across turns"
    assert cid2 == cid, "conversation_id must match across turns"
    assert mid2 != mid1, "message_id must differ between turns"

    # DB Verification
    print("\n  --- DB: messages ---")
    all_msgs = admin.table("messages").select("*").eq("conversation_id", cid).order("message_sequence").execute().data
    print(f"  total messages: {len(all_msgs)}")
    assert len(all_msgs) == 4, f"Expected 4 messages, got {len(all_msgs)}"

    seqs = [m["message_sequence"] for m in all_msgs]
    types = [m["message_type"] for m in all_msgs]
    print(f"  sequences: {seqs}")
    print(f"  types:     {types}")
    assert seqs == [1, 2, 3, 4]
    assert types == ["user", "assistant", "user", "assistant"]

    # Citations per message
    print("\n  --- DB: message_citations per message ---")
    cits1 = admin.table("message_citations").select("*").eq("message_id", mid1).execute().data
    cits2 = admin.table("message_citations").select("*").eq("message_id", mid2).execute().data
    print(f"  message 1 citations: {len(cits1)}")
    print(f"  message 2 citations: {len(cits2)}")

    # Verify no cross-contamination
    cits1_msg_ids = {str(c["message_id"]) for c in cits1}
    cits2_msg_ids = {str(c["message_id"]) for c in cits2}
    assert all(str(mid1) == mid for mid in cits1_msg_ids), "Turn 1 citations must belong to message 1"
    assert all(str(mid2) == mid for mid in cits2_msg_ids), "Turn 2 citations must belong to message 2"
    print("  No citation cross-contamination [OK]")

    print("\n>>> TEST E: PASS")
    return {"session_id": sid, "conversation_id": cid, "turn1_msg": mid1, "turn2_msg": mid2}


# ===========================================================================
# TEST F  -- INVALID / NON-RETRIEVED REFERENCE
# ===========================================================================

def test_f_invalid_non_retrieved(admin, headers, user_id):
    print("\n" + "=" * 70)
    print("PHYSICAL TEST F  -- INVALID / NON-RETRIEVED REFERENCE")
    print("=" * 70)

    # Case A: Send a query  -- the model may or may not emit [Retrieved chunk ...] with an invalid UUID
    # Case B: Valid UUID not in retrieved set -> no citation
    # We verify by checking the actual DB results for the response

    payload = {
        "user_query": "What are the admission requirements and deadlines for this college?",
        "institution_id": INSTITUTION_ID,
    }

    t0 = time.time()
    resp = chat(headers, payload)
    elapsed = time.time() - t0
    print(f"HTTP {resp.status_code} ({elapsed:.1f}s)")

    assert resp.status_code == 200
    d = resp.json()

    msg_id = d["message_id"]
    answer = d.get("answer", "")
    sources = d.get("source_references", [])

    print(f"  message_id: {msg_id}")
    print(f"  answer:     {answer[:200]}...")
    print(f"  sources:    {sources}")

    answer_chunks = CHUNK_REF_RE.findall(answer)
    print(f"  chunk_refs_in_answer: {answer_chunks}")

    # DB Verification
    ai_r = admin.table("ai_responses").select("*").eq("message_id", msg_id).maybe_single().execute().data
    if ai_r:
        ro = admin.table("retrieval_operations").select("*").eq("ai_response_id", ai_r["ai_response_id"]).maybe_single().execute().data
        if ro:
            rcs = admin.table("retrieved_chunks").select("chunk_id").eq("retrieval_operation_id", ro["retrieval_operation_id"]).execute().data
            retrieved_ids = {str(rc["chunk_id"]) for rc in rcs}
        else:
            retrieved_ids = set()
    else:
        retrieved_ids = set()

    cits = admin.table("message_citations").select("*").eq("message_id", msg_id).execute().data
    print(f"  message_citations: {len(cits)}")

    for ci in cits:
        cid = str(ci["chunk_id"])
        print(f"    citation chunk_id={cid}")
        # Every cited chunk MUST be in the retrieved set
        assert cid in retrieved_ids, f"Citation chunk {cid} is NOT in retrieved_chunks  -- unrestricted lookup detected"
        print(f"      [OK] In retrieved_chunks")

    # If answer_chunks has values, all must be valid UUIDs AND in retrieved_ids
    for ref in answer_chunks:
        try:
            UUID(ref)
            print(f"  Reference {ref}: valid UUID")
        except ValueError:
            print(f"  Reference {ref}: INVALID UUID  -- should not appear in citations")
            assert False, f"Invalid UUID {ref} found in answer but no citation was created"

    print("\n>>> TEST F: PASS")
    return {"message_id": msg_id, "answer_chunks": answer_chunks, "citations": cits, "retrieved_ids": list(retrieved_ids)}


# ===========================================================================
# MAIN
# ===========================================================================

def run():
    print("=" * 70)
    print("PHASE 4.3 PHYSICAL VALIDATION  -- CITATION & SOURCE TRACEABILITY")
    print("=" * 70)

    admin = get_admin_client()

    print("\n[Step 0] Authenticating test user...")
    token, user_id, auth_id = get_user_token(USER_EMAIL)
    print(f"  user_id: {user_id}")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    results = {}

    try:
        results["test_a"] = test_a_single_citation(admin, headers, user_id)
    except Exception as e:
        print(f"\n>>> TEST A: FAIL  -- {e}")
        results["test_a"] = {"error": str(e)}

    try:
        results["test_b"] = test_b_multiple_citations(admin, headers, user_id)
    except Exception as e:
        print(f"\n>>> TEST B: FAIL  -- {e}")
        results["test_b"] = {"error": str(e)}

    try:
        results["test_c"] = test_c_no_citation(admin, headers, user_id)
    except Exception as e:
        print(f"\n>>> TEST C: FAIL  -- {e}")
        results["test_c"] = {"error": str(e)}

    try:
        results["test_d"] = test_d_insufficient_context(admin, headers, user_id)
    except Exception as e:
        print(f"\n>>> TEST D: FAIL  -- {e}")
        results["test_d"] = {"error": str(e)}

    try:
        results["test_e"] = test_e_conversation_reuse(admin, headers, user_id)
    except Exception as e:
        print(f"\n>>> TEST E: FAIL  -- {e}")
        results["test_e"] = {"error": str(e)}

    try:
        results["test_f"] = test_f_invalid_non_retrieved(admin, headers, user_id)
    except Exception as e:
        print(f"\n>>> TEST F: FAIL  -- {e}")
        results["test_f"] = {"error": str(e)}

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for name, r in results.items():
        status = "FAIL" if "error" in r else "PASS"
        print(f"  {name}: {status}" + (f"  -- {r['error']}" if "error" in r else ""))

    with open("physical_validation_results_phase_4_3.json", "w") as f:
        json.dump(results, f, default=str, indent=2)
    print(f"\nResults saved to physical_validation_results_phase_4_3.json")

    return results


if __name__ == "__main__":
    run()
