"""Debug: check if entries table exists in the database."""
import sys
sys.path.insert(0, '.')
from app.db.supabase import get_admin_client

db = get_admin_client()

# Try to find entries table via information_schema
try:
    result = db.table('information_schema.tables').select('table_name').eq('table_schema', 'public').eq('table_name', 'entries').execute()
    if result.data:
        print(f'entries table exists: {result.data}')
    else:
        print('entries table NOT found in information_schema')
except Exception as e:
    print(f'information_schema query failed: {e}')

# Try direct table access
try:
    rows = db.table('entries').select('*').limit(1).execute()
    print(f'entries table accessible: {rows.data is not None}')
except Exception as e:
    print(f'entries table access failed: {e}')

# Try using the Supabase Admin API directly
try:
    from supabase import create_client
    import os
    url = os.getenv('SUPABASE_URL', 'https://rjnfmjcvkfotneswpygr.supabase.co')
    with open('.env') as f:
        env_content = f.read()
    key = env_content.split('SUPABASE_SERVICE_ROLE_KEY=')[1].splitlines()[0].strip()
    supabase = create_client(url, key)
    tables = supabase.table('information_schema.tables').select('table_name').eq('table_schema', 'public').eq('table_name', 'entries').execute()
    print(f'Supabase client info_schema: {tables.data}')
except Exception as e:
    print(f'Supabase client check failed: {e}')

# Try accessing via the admin client's schema cache directly
try:
    # The admin_client might have cached schema - try a different table name
    result2 = db.table('public.entries').select('*').limit(1).execute()
    print(f'public.entries: {result2.data is not None}')
except Exception as e:
    print(f'public.entries failed: {e}')