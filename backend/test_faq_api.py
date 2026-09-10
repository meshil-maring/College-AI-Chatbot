"""FAQ publish + delete test."""
import sys, os, httpx
sys.path.insert(0, '.')
from app.db.supabase import get_admin_client, create_supabase_client

def get_token():
    admin = get_admin_client()
    client = create_supabase_client()
    link = admin.auth.admin.generate_link({'type': 'magiclink', 'email': 'admin.demo@collegelocal.dev'})
    otp = link.properties.email_otp
    resp = client.auth.verify_otp({'email': 'admin.demo@collegelocal.dev', 'token': otp, 'type': 'magiclink'})
    return resp.session.access_token

token = get_token()
headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
BASE = 'http://127.0.0.1:8005'

with httpx.Client(timeout=60.0) as c:
    # Create
    r = c.post(BASE + '/api/v1/admin/faqs', headers=headers, json={
        'institution_id': '30000000-0000-0000-0000-000000000001',
        'category': 'general',
        'question': 'Publish test FAQ',
        'answer': 'Publish test answer.',
        'is_active': True,
    })
    print('Create:', r.status_code)
    faq_id = r.json()['faq_id']
    print('FAQ ID:', faq_id)

    # Publish
    r2 = c.post(BASE + '/api/v1/admin/faqs/' + faq_id + '/publish', headers=headers)
    print('Publish:', r2.status_code)
    print('Publish body:', r2.text)
    pub_data = r2.json() if r2.status_code == 200 else {}
    print('published =', pub_data.get('is_published'))

    # Delete
    r3 = c.delete(BASE + '/api/v1/admin/faqs/' + faq_id, headers=headers)
    print('Delete:', r3.status_code)
    print('Delete body:', r3.text)

    # Verify gone
    r4 = c.get(BASE + '/api/v1/admin/faqs/' + faq_id, headers=headers)
    print('Get after delete:', r4.status_code)