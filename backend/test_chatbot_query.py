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
headers = {'Authorization': 'Bearer ' + token}
BASE_URL = 'http://127.0.0.1:8005'

with httpx.Client(timeout=60.0) as http:
    url = BASE_URL + '/api/v1/chat/new?user_id=30000000-0000-0000-0000-000000000102&institution_id=30000000-0000-0000-0000-000000000001'
    r = http.post(url, headers=headers, json={
        'user_query': 'What is the attendance policy FAQ Test? Give exact answer.',
    })
    print('Chat response:', r.status_code)
    print(r.text[:1500])
