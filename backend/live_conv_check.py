import json, time, httpx
from test_physical_phase_4_2 import get_user_token, USER_1_EMAIL, INSTITUTION_ID

token, uid, aid = get_user_token(USER_1_EMAIL)
headers = {"Authorization": f"Bearer {token}"}
BASE = "http://127.0.0.1:8000/api/v1/generation/chat"


def ask(query: str, session_id: str):
    t0 = time.perf_counter()
    r = httpx.post(BASE, json={"user_query": query, "institution_id": INSTITUTION_ID, "session_id": session_id}, headers=headers, timeout=180.0)
    dt = (time.perf_counter() - t0) * 1000
    data = r.json()
    diag = (data.get("metadata") or {}).get("diagnostics") or {}
    print(f"Q: {query}")
    print(f"   status={r.status_code} wall={dt:.0f}ms rewrite_skipped={diag.get('query_rewrite_skipped')} rewrite={diag.get('query_rewrite_latency_ms')}ms in={diag.get('final_input_token_count')} out={diag.get('output_token_count')}")
    print(f"   answer={data.get('answer', '')[:160]!r}")
    print(f"   rewritten_query={diag.get('rewritten_query')!r}")
    print(f"   refs={[s.get('quote','')[:50] for s in (data.get('sources') or [])]}")
    rundt = round(dt, 1)
    return data, diag, rundt


def run_sequence():
    results = []
    sid = "0c0c0c0c-0000-4000-8000-000000000001"
    qs = [
        "How much is the annual hostel fee for a standard room?",
        "What about for girls?",
        "What about boys?",
        "What about AC?",
        "Is the deposit refundable?",
    ]
    for i, q in enumerate(qs, start=1):
        data, diag, dt = ask(q, sid)
        results.append({"step": f"Q{i}", "query": q, "wall_ms": dt,
                        "rewrite_skipped": diag.get("query_rewrite_skipped"),
                        "rewritten_query": diag.get("rewritten_query"),
                        "answer": (data.get("answer") or "")[:200],
                        "status": r if (r := data.get("status")) else None})
        time.sleep(0.5)

    sid2 = "0c0c0c0c-0000-4000-8000-000000000002"
    for name, q in [
        ("security-deposit", "How much is the hostel security deposit?"),
        ("academic", "What is the minimum attendance required to appear for the semester examination?"),
        ("unrelated", "What is the capital of France?"),
    ]:
        data, diag, dt = ask(q, sid2)
        results.append({"step": name, "query": q, "wall_ms": dt,
                        "rewrite_skipped": diag.get("query_rewrite_skipped"),
                        "rewritten_query": diag.get("rewritten_query"),
                        "answer": (data.get("answer") or "")[:200],
                        "status": data.get("status")})
        time.sleep(0.5)

    with open("live_conv_check.json", "w") as f:
        json.dump({"token_user": str(uid), "results": results}, f, indent=2)
    print("\n=== SUMMARY ===")
    for rec in results:
        print(f"{rec['step']:18s} status={rec['status']} wall={rec['wall_ms']:7.0f}ms rewrite_skipped={rec['rewrite_skipped']} rewritten={rec['rewritten_query']}")
        print(f"   answer={rec['answer']!r}")


if __name__ == "__main__":
    run_sequence()