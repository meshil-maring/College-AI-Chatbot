"""Temporary script to inspect the remote Supabase database schema."""

import json

from supabase import create_client

from app.config import settings


def get_columns(client, table_name):
    """Get column names for a table using the PostgREST head request."""
    try:
        # Use select with head to get only schema, no data
        from postgrest.exceptions import PostgrestException
    except ImportError:
        pass
    try:
        resp = client.table(table_name).select("*").head().execute()
        # The schema info is in resp's headers or we can use a workaround
        # Actually, let's use the postgrest schema endpoint
        # Fall back: just try selecting known columns
        return None
    except Exception:
        return None


def try_select_columns(client, table_name, columns):
    """Try selecting specific columns to verify they exist."""
    cols_str = ", ".join(columns)
    try:
        resp = client.table(table_name).select(cols_str).limit(0).execute()
        return columns
    except Exception as e:
        # Try each column individually
        valid = []
        for col in columns:
            try:
                client.table(table_name).select(col).limit(0).execute()
                valid.append(col)
            except Exception:
                pass
        return valid


def get_sample(client, table_name, n=3):
    """Get sample rows to understand the schema."""
    try:
        resp = client.table(table_name).select("*").limit(n).execute()
        if resp.data:
            return resp.data
        return None
    except Exception as e:
        return {"error": str(e)}


def main():
    admin = create_client(settings.supabase_url, settings.supabase_secret_key)

    # Verify key column names for tables we'll reference
    print("=== users table ===")
    print("Trying columns:", try_select_columns(admin, "users",
          ["user_id", "id", "auth_user_id", "email", "first_name", "last_name",
           "display_name", "status", "created_at", "updated_at", "last_login_at"]))
    sample = get_sample(admin, "users")
    print("Sample:", json.dumps(sample, indent=2, default=str)[:500] if sample else "None")

    print("\n=== roles table ===")
    print("Trying columns:", try_select_columns(admin, "roles",
          ["id", "name", "description", "is_active", "created_at", "updated_at"]))
    sample = get_sample(admin, "roles")
    print("Sample:", json.dumps(sample, indent=2, default=str)[:500] if sample else "None")

    print("\n=== user_roles table ===")
    print("Trying columns:", try_select_columns(admin, "user_roles",
          ["user_id", "role_id", "assigned_at"]))
    sample = get_sample(admin, "user_roles")
    print("Sample:", json.dumps(sample, indent=2, default=str)[:500] if sample else "None")

    print("\n=== institutions table ===")
    print("Trying columns:", try_select_columns(admin, "institutions",
          ["institution_id", "name", "code", "is_active", "created_at", "updated_at"]))
    sample = get_sample(admin, "institutions")
    print("Sample:", json.dumps(sample, indent=2, default=str)[:500] if sample else "None")

    print("\n=== departments table ===")
    print("Trying columns:", try_select_columns(admin, "departments",
          ["department_id", "institution_id", "name", "code", "is_active"]))
    sample = get_sample(admin, "departments")

    print("\n=== programs table ===")
    print("Trying columns:", try_select_columns(admin, "programs",
          ["program_id", "department_id", "name", "code", "degree_type", "is_active"]))
    sample = get_sample(admin, "programs")
    print("Sample:", json.dumps(sample, indent=2, default=str)[:500] if sample else "None")

    print("\n=== courses table ===")
    print("Trying columns:", try_select_columns(admin, "courses",
          ["course_id", "department_id", "name", "code", "credits", "is_active"]))

    print("\n=== course_offerings table ===")
    print("Trying columns:", try_select_columns(admin, "course_offerings",
          ["course_offering_id", "course_id", "academic_year_id", "semester_id",
           "program_id", "is_active"]))

    print("\n=== sections table ===")
    print("Trying columns:", try_select_columns(admin, "sections",
          ["section_id", "course_offering_id", "name", "code", "is_active"]))

    print("\n=== semesters table ===")
    print("Trying columns:", try_select_columns(admin, "semesters",
          ["semester_id", "academic_year_id", "name", "code", "semester_number",
           "is_current", "is_active"]))

    print("\n=== academic_years table ===")
    print("Trying columns:", try_select_columns(admin, "academic_years",
          ["academic_year_id", "institution_id", "name", "code", "start_date",
           "end_date", "is_current", "is_active"]))
    sample = get_sample(admin, "academic_years")
    print("Sample:", json.dumps(sample, indent=2, default=str)[:500] if sample else "None")

    # Check if new tables exist
    for tbl in ["students", "student_results", "student_result_items",
                "test_results", "student_attendance", "faqs", "notices",
                "admin_audit_log"]:
        try:
            admin.table(tbl).select("*").limit(0).execute()
            print(f"\n{tbl}: EXISTS")
        except Exception as e:
            print(f"\n{tbl}: not found - {e}")

    # Check existing data
    print("\n=== Existing data counts ===")
    for tbl in ["users", "roles", "user_roles", "institutions", "departments",
                "programs", "courses", "course_offerings", "sections",
                "semesters", "academic_years"]:
        try:
            resp = admin.table(tbl).select("*", count="exact").limit(0).execute()
            print(f"  {tbl}: {resp.count} rows")
        except Exception as e:
            print(f"  {tbl}: error - {e}")


if __name__ == "__main__":
    main()
