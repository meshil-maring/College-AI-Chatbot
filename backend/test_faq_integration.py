"""Test FAQ publish flow with real token."""
import sys
sys.path.insert(0, '.')
import httpx
from app.db.supabase import get_admin_client, create_supabase_client

BASE_URL = 'http://127.0.0.1:8005'

def main():
    admin = get_admin_client()
    client = create_supabase_client()
    link = admin.auth.admin.generate_link({'type': 'magiclink', 'email': 'admin.demo@collegelocal.dev'})
    otp = link.properties.email_otp
    resp = client.auth.verify_otp({'email': 'admin.demo@collegelocal.dev', 'token': otp, 'type': 'magiclink'})
    token = resp.session.access_token
    headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}

    with httpx.Client(timeout=60.0) as http:
        r = http.post(BASE_URL + '/api/v1/admin/faqs', headers=headers, json={
            'institution_id': '30000000-0000-0000-0000-000000000001',
            'category': 'general',
            'question': 'Test FAQ for publish flow',
            'answer': 'Test answer text.',
            'is_active': True,
        })
        print('Create:', r.status_code)
        if r.status_code >= 300:
            print('ERROR:', r.text[:300])
            return
        faq_id = r.json()['faq_id']
        print('FAQ ID:', faq_id)

        r2 = http.post(BASE_URL + '/api/v1/admin/faqs/' + str(faq_id) + '/publish', headers=headers)
        print('Publish:', r2.status_code)
        if r2.status_code >= 300:
            print('ERROR:', r2.text[:300])

        r3 = http.get(BASE_URL + '/api/v1/admin/faqs/' + str(faq_id), headers=headers)
        print('Get:', r3.status_code)
        if r3.status_code == 200:
            item = r3.json()
            print('published=', item.get('is_published'))

        r4 = http.delete(BASE_URL + '/api/v1/admin/faqs/' + str(faq_id), headers=headers)
        print('Delete:', r4.status_code)
        if r4.status_code >= 300:
            print('ERROR:', r4.text[:300])

        r5 = http.get(BASE_URL + '/api/v1/admin/faqs/' + str(faq_id), headers=headers)
        print('Get after delete:', r5.status_code, '(expected 404)')

    print('\n=== DONE ===')

if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)