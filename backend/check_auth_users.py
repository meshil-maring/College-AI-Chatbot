"""Test inserting into auth.users via schema() and check columns."""

import json

from supabase import create_client
from app.config import settings


def main():
    admin = create_client(settings.supabase_url, settings.supabase_secret_key)

    # Try accessing auth.users via .schema()
    print("=== Try auth.users via .schema('auth') ===")
    try:
        resp = admin.schema("auth").table("users").select("*").limit(1).execute()
        print("auth.users columns:", list(resp.data[0].keys()) if resp.data else "no data")
        print("auth.users sample:", json.dumps(resp.data, indent=2, default=str)[:800])
    except Exception as e:
        print(f"auth.users via schema() error: {e}")

    # Try selecting specific columns from auth.users
    print("\n=== Try auth.users column probing ===")
    test_cols = ["id", "email", "encrypted_password", "email_confirmed_at",
                 "created_at", "updated_at", "role", "aud", "app_metadata",
                 "user_metadata", "confirmed_at", "instance_id", "identities"]
    valid_cols = []
    for col in test_cols:
        try:
            admin.schema("auth").table("users").select(col).limit(0).execute()
            valid_cols.append(col)
        except Exception:
            pass
    print(f"Valid auth.users columns: {valid_cols}")

    # Try inserting a test auth user
    print("\n=== Try inserting into auth.users ===")
    test_auth_id = "40000000-0000-0000-0000-000000000999"
    try:
        resp = admin.schema("auth").table("users").insert({
            "id": test_auth_id,
            "email": "test-validation@collegeai.local",
            "encrypted_password": "test",
            "email_confirmed_at": "2026-09-09T00:00:00.000000+00:00",
            "created_at": "2026-09-09T00:00:00.000000+00:00",
            "updated_at": "2026-09-09T00:00:00.000000+00:00",
            "role": "authenticated",
            "aud": "authenticated",
            "app_metadata": {},
            "user_metadata": {},
        }).execute()
        print("Auth user insert SUCCESS:", json.dumps(resp.data, indent=2, default=str))

        # Now try inserting into public.users referencing this auth user
        try:
            resp2 = admin.table("users").insert({
                "user_id": "30000000-0000-0000-0000-000000000999",
                "auth_user_id": test_auth_id,
                "email": "test-validation@collegeai.local",
                "first_name": "Test",
                "last_name": "Validation",
                "display_name": "Test Validation",
                "status": "active",
            }).execute()
            print("public.users insert SUCCESS:", json.dumps(resp2.data, indent=2, default=str))
        except Exception as e2:
            print(f"public.users insert error: {e2}")

    except Exception as e:
        print(f"auth.users insert error: {e}")
    finally:
        # Clean up - delete the test auth user and public users
        try:
            admin.schema("auth").table("users").delete().eq("id", test_auth_id).execute()
            print("Test auth user cleaned up.")
        except Exception:
            pass
        try:
            admin.table("users").delete().eq("user_id", "30000000-0000-0000-0000-000000000999").execute()
            print("Test public.users row cleaned up.")
        except Exception:
            pass

    # Get full course_offerings data
    print("\n=== ALL COURSE_OFFERINGS ===")
    resp = admin.table("course_offerings").select(
        "course_offering_id, course_id, academic_year_id, semester_id, program_id, capacity"
    ).execute()
    print(json.dumps(resp.data, indent=2, default=str))

    # Get departments details
    print("\n=== ALL DEPARTMENTS ===")
    resp = admin.table("departments").select("*").execute()
    print(json.dumps(resp.data, indent=2, default=str))

    # Get second academic year
    print("\n=== ALL ACADEMIC_YEARS ===")
    resp = admin.table("academic_years").select("*").execute()
    print(json.dumps(resp.data, indent=2, default=str))


if __name__ == "__main__":
    main()
