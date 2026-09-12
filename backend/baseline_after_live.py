import sys, time, json, httpx

from test_physical_phase_4_2 import get_user_token, USER_1_EMAIL, INSTITUTION_ID

token, uid, aid = get_user_token(USER_1_EMAIL)
headers = {'Authorization': f'Bearer {token}'}

tests = [
    ('A standalone academic', 'What is the minimum attendance required to appear for the semester examination?'),
    ('B conversational followup', "What about for final year students?"),
    ('C hostel', 'How much is the annual hostel fee for a standard room?'),
    ('D unrelated', 'What is the capital of France?'),
]

results = []
for name, q in tests:
    t0 = time.perf_counter()
    r = httpx.post('http://127.0.0.1:8000/api/v1/generation/chat', json={
        'user_query': q, 'institution_id': INSTITUTION_ID,
    }, headers=headers, timeout=180.0)
    dt = (time.perf_counter() - t0) * 1000
    data = r.json()
    usage = data.get('usage') or {}
    diag = (data.get('metadata') or {}).get('diagnostics') or {}
    results.append({
        'name': name,
        'query': q,
        'status_code': r.status_code,
        'wall_ms': round(dt, 1),
        'input_tokens': usage.get('input_tokens'),
        'output_tokens': usage.get('output_tokens'),
        'diagnostics': diag,
        'answer_preview': (data.get('answer') or '')[:80],
        'error': data if r.status_code != 200 else None,
    })
    sc = r.status_code
    print(f"{name}: status={sc} wall={dt:.0f}ms in={usage.get('input_tokens')} out={usage.get('output_tokens')}")
    print(f"   answer={data.get('answer','')[:90]!r}")
    print(f"   diag={json.dumps(diag)}")
    if sc != 200:
        print(f"   ERROR: {json.dumps(data, indent=2)[:400]}")
    print()

summary = []
for r in results:
    summary.append((r['name'], r['wall_ms'], r['input_tokens'], r['output_tokens'], r['status_code']))
print('=' * 60)
print('AFTER SUMMARY')
for name, w, it, ot, sc in summary:
    print(f"{name:30s} wall={w:10.0f}ms  in={it:5}  out={ot:5}  status={sc}")

with open('baseline_after_final.json', 'w') as f:
    json.dump(results, f, indent=2)
print('\nSaved baseline_after_final.json')