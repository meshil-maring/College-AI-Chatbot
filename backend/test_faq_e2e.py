import sys
sys.path.insert(0, '.')
import httpx
from app.db.supabase import get_admin_client, create_supabase_client

admin = get_admin_client()
client = create_supabase_client()
link = admin.auth.admin.generate_link({'type': 'magiclink', 'email': 'admin.demo@collegelocal.dev'})
otp = link.properties.email_otp
resp = client.auth.verify_otp({'email': 'admin.demo@collegelocal.dev', 'token': otp, 'type': 'magiclink'})
token = resp.session.access_token
headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
BASE_URL = 'http://127.0.0.1:8005'

with httpx.Client(timeout=60.0) as http:
    # CREATE
    r = http.post(BASE_URL + '/api/v1/admin/faqs', headers=headers, json={
        'institution_id': '30000000-0000-0000-0000-000000000001',
        'category': 'general',
        'question': 'What is the attendance policy FAQ Test?',
        'answer': 'You must attend at least 75 percent of classes. If attendance falls below 75 percent you are not allowed to sit the regular end semester exam.',
        'is_active': True,
    })
    print('CREATE:', r.status_code)
    print('Body:', r.text[:300])
    if r.status_code != 201:
        print('FATAL: Cannot proceed')
        sys.exit(1)
    faq_id = r.json()['faq_id']
    print('FAQ ID:', faq_id)
    print()

    # PUBLISH
    r2 = http.post(BASE_URL + '/api/v1/admin/faqs/' + faq_id + '/publish', headers=headers)
    print('PUBLISH:', r2.status_code)
    print('Body:', r2.text[:300])
    print()

    # VERIFY PUBLISHED STATE
    r3 = http.get(BASE_URL + '/api/v1/admin/faqs/' + faq_id, headers=headers)
    print('GET:', r3.status_code)
    if r3.status_code == 200:
        item = r3.json()
        print('published:', item.get('is_published'))
        print('has_doc:', item.get('document_id') is not None)
    print()

    # CHAT QUERY - verify retrieval
    url = BASE_URL + '/api/v1/chat/new?user_id=30000000-0000-0000-0000-000000000102&institution_id=30000000-0000-0000-0000-000000000001'
    r4 = http.post(url, headers=headers, json={'user_query': 'What is the attendance policy? Give exact answer.'})
    print('CHAT:', r4.status_code)
    if r4.status_code == 200:
        data = r4.json()
        print('Answer:', data.get('answer', '')[:500])
        refs = data.get('source_references', [])
        print('References:', len(refs))
        for ref in refs[:3]:
            print('  -', ref.get('title', ''), ref.get('source_type', ''))
    print()

    # DELETE
    r5 = http.delete(BASE_URL + '/api/v1/admin/faqs/' + faq_id, headers=headers)
    print('DELETE:', r5.status_code)
    print('Body:', r5.text[:300])
    print()

    # VERIFY DELETED
    r6 = http.get(BASE_URL + '/api/v1/admin/faqs/' + faq_id, headers=headers)
    print('GET after delete:', r6.status_code, '(expected 404)')
