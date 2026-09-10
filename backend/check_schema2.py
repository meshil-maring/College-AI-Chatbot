"""Inspect auth.users table and check for run_sql RPC, and get full data dump."""

import json
import os

from supabase import create_client

from app.config import settings


def main():
    admin = create_client(settings.supabase_url, settings.supabase_secret_key)

    # Try to query auth.users to understand the structure
    print("=== Trying auth.users table via admin ===")
    try:
        # The auth schema might not be exposed via PostgREST, try via rpc
        resp = admin.rpc("run_sql", {"query":
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_schema = 'auth' AND table_name = 'users' "
            "ORDER BY ordinal_position"
        }).execute()
        print("auth.users columns:", json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"run_sql RPC error: {e}")

    # Try to get a sample from auth.users
    try:
        resp = admin.rpc("run_sql", {"query":
            "SELECT id, email, email_confirmed_at, created_at, role, aud "
            "FROM auth.users LIMIT 5"
        }).execute()
        print("\nauth.users sample:", json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"auth.users sample error: {e}")

    # Check existing auth.users count
    try:
        resp = admin.rpc("run_sql", {"query":
            "SELECT COUNT(*) as cnt FROM auth.users"
        }).execute()
        print("\nauth.users count:", json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"auth.users count error: {e}")

    # Check if there's an admin user in auth.users
    try:
        resp = admin.rpc("run_sql", {"query":
            "SELECT id, email, role FROM auth.users "
            "WHERE email IN ('admin.iridix@gmail.com', 'dsmeshilmaring13@gmail.com') "
            "ORDER BY email"
        }).execute()
        print("\nexisting auth users (admin/faculty):", json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"existing auth users error: {e}")

    # List all tables in public schema
    try:
        resp = admin.rpc("run_sql", {"query":
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        }).execute()
        print("\n=== ALL public tables ===")
        print(json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"list tables error: {e}")

    # Get the FULL list of roles
    try:
        resp = admin.table("roles").select("role_id, name, description, is_active").execute()
        print("\n=== ALL ROLES (full) ===")
        print(json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"roles error: {e}")

    # Get the FULL list of users
    try:
        resp = admin.table("users").select("*").execute()
        print("\n=== ALL USERS (full) ===")
        print(json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"users error: {e}")

    # Get all course_offerings with details
    try:
        resp = admin.table("course_offerings").select(
            "course_offering_id, course_id, academic_year_id, semester_id, program_id, capacity"
        ).execute()
        print("\n=== ALL COURSE_OFFERINGS (full) ===")
        print(json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"course_offerings error: {e}")

    # Get all sections with details
    try:
        resp = admin.table("sections").select(
            "section_id, course_offering_id, name, code, capacity"
        ).execute()
        print("\n=== ALL SECTIONS (full) ===")
        print(json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"sections error: {e}")

    # Get all semesters
    try:
        resp = admin.table("semesters").select(
            "semester_id, academic_year_id, name, code, semester_number, start_date, end_date, is_current, is_active"
        ).execute()
        print("\n=== ALL SEMESTERS (full) ===")
        print(json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"semesters error: {e}")

    # Get all courses
    try:
        resp = admin.table("courses").select(
            "course_id, department_id, name, code, credits, is_active"
        ).execute()
        print("\n=== ALL COURSES (full) ===")
        print(json.dumps(resp.data, indent=2, default=str))
    except Exception as e:
        print(f"courses error: {e}")


if __name__ == "__main__":
    main()

