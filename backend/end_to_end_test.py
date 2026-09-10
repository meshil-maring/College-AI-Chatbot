"""ADMIN-5 End-to-End Integration Test Suite."""
import sys, os, time
sys.path.insert(0, '.')

import httpx
from app.db.supabase import get_admin_client, create_supabase_client
from uuid import UUID, uuid4

BASE_URL = os.environ.get('ADMIN5_BASE_URL', 'http://127.0.0.1:8005')
INSTITUTION_ID = '30000000-0000-0000-0000-000000000001'
ADMIN_EMAIL = 'admin.demo@collegelocal.dev'
STUDENT_EMAIL = 'student.demo@collegelocal.dev'

class R:
    pass

def get_token(email):
    admin = get_admin_client()
    client = create_supabase_client()
    link = admin.auth.admin.generate_link({'type': 'magiclink', 'email': email})
    otp = link.properties.email_otp
    resp = client.auth.verify_otp({'email': email, 'token': otp, 'type': 'magiclink'})
    return resp.session.access_token

ADMIN_TOKEN = None
STUDENT_TOKEN = None

def get_token(email):
    admin_client = get_admin_client()
    client = create_supabase_client()
    link = admin_client.auth.admin.generate_link({'type': 'magiclink', 'email': email})
    otp = link.properties.email_otp
    resp = client.auth.verify_otp({'email': email, 'token': otp, 'type': 'magiclink'})
    return resp.session.access_token

def ah():
    global ADMIN_TOKEN
    if ADMIN_TOKEN is None:
        ADMIN_TOKEN = get_token(ADMIN_EMAIL)
    return {'Authorization': f'Bearer {ADMIN_TOKEN}', 'Content-Type': 'application/json'}

def sh():
    global STUDENT_TOKEN
    if STUDENT_TOKEN is None:
        STUDENT_TOKEN = get_token(STUDENT_EMAIL)
    return {'Authorization': f'Bearer {STUDENT_TOKEN}', 'Content-Type': 'application/json'}

def ok(name, cond):
    print(f'  [{"PASS" if cond else "FAIL"}] {name}')
    return cond

def get_token(email):
    admin_client = get_admin_client()
    client = create_supabase_client()
    link = admin_client.auth.admin.generate_link({'type': 'magiclink', 'email': email})
    otp = link.properties.email_otp
    resp = client.auth.verify_otp({'email': email, 'token': otp, 'type': 'magiclink'})
    return resp.session.access_token

ADMIN_TOKEN = None
STUDENT_TOKEN = None

def ah():
    global ADMIN_TOKEN
    if ADMIN_TOKEN is None:
        ADMIN_TOKEN = get_token(ADMIN_EMAIL)
    return {'Authorization': f'Bearer {ADMIN_TOKEN}', 'Content-Type': 'application/json'}

def sh():
    global STUDENT_TOKEN
    if STUDENT_TOKEN is None:
        STUDENT_TOKEN = get_token(STUDENT_EMAIL)
    return {'Authorization': f'Bearer {STUDENT_TOKEN}', 'Content-Type': 'application/json'}

def ok(name, cond):
    print(f'  [{"PASS" if cond else "FAIL"}] {name}')
    return cond
