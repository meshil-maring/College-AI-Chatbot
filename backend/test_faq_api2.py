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

def test():
    with httpx.Client(timeout=60.0) as http:
        # 1. Create FAQ
        r = http.post(BASE_URL + '/api/v1/admin/faqs', headers=headers, json={
            'institution_id': '30000000-0000-0000-0000-000000000001',
            'category': 'general',
            'question': 'What is the attendance policy FAQ Test?',
            'answer': 'You must attend 75 percent of all classes to sit exams.',
            'is_active': True,
        })
        print('1. CREATE FAQ:', r.status_code)
        print('   Body:', r.text[:300])
        if r.status_code != 201:
            print('FATAL: Cannot create FAQ')
            return
        faq_id = r.json()['faq_id']
        print('   FAQ ID:', faq_id)
        print()

        # 2. Update FAQ
        r2 = http.patch(BASE_URL + '/api/v1/admin/faqs/' + faq_id, headers=headers, json={
            'answer': 'Updated: You must attend 80 percent of classes.',
        })
        print('2. UPDATE FAQ:', r2.status_code)
        print('   Body:', r2.text[:300] if r2.status_code >= 400 else r2.text[:200])
        print()

        # 3. Publish FAQ
        r3 = http.post(BASE_URL + '/api/v1/admin/faqs/' + faq_id + '/publish', headers=headers)
        print('3. PUBLISH FAQ:', r3.status_code)
        print('   Body:', r3.text[:500])
        print()

        # 4. Get published FAQ
        r4 = http.get(BASE_URL + '/api/v1/admin/faqs/' + faq_id, headers=headers)
        print('4. GET FAQ:', r4.status_code)
        if r4.status_code == 200:
            item = r4.json()
            pub = item.get('is_published')
            has_doc = item.get('document_id') is not None
            print('   published:', pub)
            print('   has_document:', has_doc)
            if has_doc:
                print('   doc_id:', item.get('document_id'))
        print()

        # 5. Verify RAG retrieval via chatbot
        url = BASE_URL + '/api/v1/chat/new?user_id=30000000-0000-0000-0000-000000000102&institution_id=30000000-0000-0000-0000-000000000001'
        r5 = http.post(url, headers=headers, json={'user_query': 'What is the attendance policy? Give the exact answer from the FAQ.'})
        print('5. CHAT RETRIEVAL:', r5.status_code)
        if r5.status_code == 200:
            data = r5.json()
            print('   Answer:', data.get('answer', '')[:500])
            refs = data.get('source_references', [])
            print('   References:', len(refs))
            for ref in refs[:5]:
                print('     -', ref.get('title', 'N/A'), '|', ref.get('source_type', 'N/A'))
        else:
            print('   Body:', r5.text[:300])
        print()

        # 6. Delete FAQ
        r6 = http.delete(BASE_URL + '/api/v1/admin/faqs/' + faq_id, headers=headers)
        print('6. DELETE FAQ:', r6.status_code)
        print('   Body:', r6.text[:500])
        print()

        # 7. Verify deleted
        r7 = http.get(BASE_URL + '/api/v1/admin/faqs/' + faq_id, headers=headers)
        print('7. GET after delete:', r7.status_code, '(expected 404)')

test()
