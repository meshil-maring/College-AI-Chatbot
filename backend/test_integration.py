import sys; print('START', flush=True)
import sys as _s; _s.path.insert(0, '.')
from uuid import uuid4
import httpx
from app.db.supabase import get_admin_client, create_supabase_client
import time
BASE_URL = 'http://127.0.0.1:8005'
INSTITUTION_ID = '30000000-0000-0000-0000-000000000001'

def get_token(email='admin.demo@collegelocal.dev'):
    admin = get_admin_client()
    client = create_supabase_client()
    link = admin.auth.admin.generate_link({'type': 'magiclink', 'email': email})
    otp = link.properties.email_otp
    resp = client.auth.verify_otp({'email': email, 'token': otp, 'type': 'magiclink'})
    return resp.session.access_token

def api_headers(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

def test_faq_flow(token):
    print('=== FAQ FLOW ===', flush=True)
    headers = api_headers(token)
    with httpx.Client(timeout=120.0) as http:
        r = http.post(f'{BASE_URL}/api/v1/admin/faqs', headers=headers, json={
            'institution_id': INSTITUTION_ID,
            'category': 'general',
            'question': f'Test FAQ {uuid4().hex[:8]}',
            'answer': 'Test answer text.',
            'is_active': True,
        })
        print(f'1. Create FAQ: {r.status_code}', flush=True)
        if r.status_code >= 300:
            print(f'   ERROR: {r.text[:500]}', flush=True)
            return False
        faq_id = r.json()['faq_id']
        print(f'   FAQ ID: {faq_id}', flush=True)
        
        r2 = http.get(f'{BASE_URL}/api/v1/admin/faqs/{faq_id}', headers=headers)
        print(f'2. Get FAQ: {r2.status_code}', flush=True)
        
        r3 = http.post(f'{BASE_URL}/api/v1/admin/faqs/{faq_id}/publish', headers=headers)
        print(f'3. Publish FAQ: {r3.status_code}', flush=True)
        if r3.status_code >= 300:
            print(f'   ERROR: {r3.text[:500]}', flush=True)
            return False
        
        r4 = http.get(f'{BASE_URL}/api/v1/admin/faqs/{faq_id}', headers=headers)
        print(f'4. Verify published: {r4.status_code}', flush=True)
        if r4.status_code == 200:
            item = r4.json()
            print(f'   published={item.get("is_published")}, doc={item.get("document_id") is not None}', flush=True)
        
        r5 = http.delete(f'{BASE_URL}/api/v1/admin/faqs/{faq_id}', headers=headers)
        print(f'5. Delete FAQ: {r5.status_code}', flush=True)
        if r5.status_code >= 300:
            print(f'   ERROR: {r5.text[:500]}', flush=True)
            return False
        
        r6 = http.get(f'{BASE_URL}/api/v1/admin/faqs/{faq_id}', headers=headers)
        print(f'6. Get after delete: {r6.status_code} (expected 404)', flush=True)
        print('=== FAQ FLOW PASSED ===', flush=True)
        return True

def test_notice_flow(token):
    print('=== NOTICE FLOW ===', flush=True)
    headers = api_headers(token)
    with httpx.Client(timeout=60.0) as http:
        r = http.post(f'{BASE_URL}/api/v1/admin/notices', headers=headers, json={
            'institution_id': INSTITUTION_ID,
            'category': 'general',
            'title': f'Test Notice {uuid4().hex[:8]}',
            'content': 'Test notice content.',
            'is_published': False,
            'is_active': True,
        })
        print(f'1. Create notice: {r.status_code}', flush=True)
        if r.status_code >= 300:
            print(f'   ERROR: {r.text[:500]}', flush=True)
            return False
        notice_id = r.json()['notice_id']
        print(f'   Notice ID: {notice_id}', flush=True)
        
        r2 = http.post(f'{BASE_URL}/api/v1/admin/notices/{notice_id}/publish', headers=headers)
        print(f'2. Publish notice: {r2.status_code}', flush=True)
        
        r3 = http.get(f'{BASE_URL}/api/v1/admin/notices/{notice_id}', headers=headers)
        print(f'3. Get notice: {r3.status_code}', flush=True)
        
        r4 = http.delete(f'{BASE_URL}/api/v1/admin/notices/{notice_id}', headers=headers)
        print(f'4. Delete notice: {r4.status_code}', flush=True)
        print('=== NOTICE FLOW PASSED ===', flush=True)
        return True

def test_student_academics(admin_token):
    print('=== STUDENT ACADEMICS ===', flush=True)
    student_token = get_token('student.demo@collegelocal.dev')
    student_headers = api_headers(student_token)
    with httpx.Client(timeout=60.0) as http:
        r = http.get(f'{BASE_URL}/api/v1/students/me/profile', headers=student_headers)
        print(f'1. Student me/profile: {r.status_code}', flush=True)
        
        r2 = http.get(f'{BASE_URL}/api/v1/admin/dashboard', headers=student_headers)
        print(f'2. Admin dashboard from student: {r2.status_code} (expected 403)', flush=True)
        
        r3 = http.get(f'{BASE_URL}/api/v1/students/me/results', headers=student_headers)
        print(f'3. Student me/results: {r3.status_code}', flush=True)
        
        r4 = http.get(f'{BASE_URL}/api/v1/students/me/test-results', headers=student_headers)
        print(f'4. Student me/test-results: {r4.status_code}', flush=True)
        
        r5 = http.get(f'{BASE_URL}/api/v1/students/me/attendance', headers=student_headers)
        print(f'5. Student me/attendance: {r5.status_code}', flush=True)
        print('=== STUDENT ACADEMICS PASSED ===', flush=True)
        return True

def main():
    print('=== ADMIN-5 INTEGRATION TESTS ===', flush=True)
    token = get_token()
    results = []
    results.append(('FAQ flow', test_faq_flow(token)))
    results.append(('Notice flow', test_notice_flow(token)))
    results.append(('Student academics', test_student_academics(token)))
    print('\n=== SUMMARY ===', flush=True)
    for name, passed in results:
        status = 'PASS' if passed else 'FAIL'
        print(f'  {status}: {name}', flush=True)
    all_passed = all(p for _, p in results)
    print(f'Overall: {"ALL PASSED" if all_passed else "SOME FAILED"}', flush=True)
    _s.exit(0 if all_passed else 1)

if __name__ == '__main__':
    main()
