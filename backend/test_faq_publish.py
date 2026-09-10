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
    r = http.post(BASE_URL + '/api/v1/admin/faqs', headers=headers, json={
        'institution_id': '30000000-0000-0000-0000-000000000001',
        'category': 'general',
        'question': 'Test FAQ for publish flow',
        'answer': 'Test answer text.',
        'is_active': True,
    })
    print('Create:', r.status_code)
    faq_id = r.json()['faq_id']
    print('FAQ ID:', faq_id)

    r2 = http.post(BASE_URL + '/api/v1/admin/faqs/' + faq_id + '/publish', headers=headers)
    print('Publish:', r2.status_code, r2.text[:300])

    r3 = http.get(BASE_URL + '/api/v1/admin/faqs/' + faq_id, headers=headers)
    print('Get:', r3.status_code)
    if r3.status_code == 200:
        item = r3.json()
        print('published:', item.get('is_published'))

    r4 = http.delete(BASE_URL + '/api/v1/admin/faqs/' + faq_id, headers=headers)
    print('Delete:', r4.status_code, r4.text[:300])

    r5 = http.get(BASE_URL + '/api/v1/admin/faqs/' + faq_id, headers=headers)
    print('Get after delete:', r5.status_code, '(expected 404)')
