# Local database and migration rehearsal

The hosted Supabase project is live. Every database change is rehearsed on a
local Supabase stack first, and database rules are tested on a real Postgres.

## One-time setup

Requirements: Docker Desktop (running) and the Supabase CLI.

```bash
supabase start                                        # from the repository root
python backend/scripts/local_stack/write_local_env.py # writes backend/.env.local
```

`backend/.env` is never edited and keeps pointing at the live project.
`backend/.env.local` (git-ignored) overrides only the database connection, and
blanks R2 storage and real email delivery so a local run cannot touch live data.

## Using the local stack from the backend

Set `BACKEND_ENV=local` for any backend command that should use the local stack:

```bash
cd backend
BACKEND_ENV=local .venv/Scripts/python -m pytest tests/academics
BACKEND_ENV=local .venv/Scripts/python -m uvicorn app.main:app --reload
```

With `BACKEND_ENV=local`, startup fails if `SUPABASE_URL` is not a local
address, so a misconfigured local run cannot reach the live project. Without
the variable, nothing changes: `.env` is read exactly as before.

Local Studio runs at <http://127.0.0.1:54323>.

## Database tests

Database tests live in `supabase/tests/database/*.test.sql` and use pgTAP. Each
file runs in a transaction that is rolled back.

```bash
supabase test db --local
```

`academic_setup_rules.test.sql` covers the Academic Setup rules: decimal credit
snapshots, publishing, batch years, section terms, capacities and tenant
isolation. Add a test whenever a trigger or constraint changes.

## Rehearsing a migration before live

1. Add the migration under `supabase/migrations/`.
2. `supabase db reset --local` replays **every** migration on a clean database.
   It must apply without errors.
3. `supabase test db --local` and the backend tests with `BACKEND_ENV=local`
   must pass.
4. `supabase db push --linked --dry-run` must list only the new migration.
5. Only then, with approval, `supabase db push --linked`.

Keep the reset, test and push output in `logs/backend/`.

## Schema drift

`supabase db diff --linked --schema public` compares the live schema with what
the migrations produce. It only reads the live schema. An empty diff means the
local rehearsal matches live. Investigate any difference before relying on a
rehearsal.

`supabase db reset` always targets the local stack unless `--linked` is passed.
Never pass `--linked` to `db reset`: it would wipe the live database.
