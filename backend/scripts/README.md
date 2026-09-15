# Backend manual and validation scripts

Out-of-suite scripts used for one-off debugging, manual API checks and "physical" validation against
a live stack. They are deliberately **not** part of `backend/tests/` (the pytest suite), and pytest
does not collect them.

## Requirements

- Real credentials in `backend/.env` (Supabase, Cloudflare R2, OpenRouter)
- A backend listening on `http://127.0.0.1:8000` for anything that calls the API
- An interpreter with the backend dependencies, e.g. `uv run python <script>` or `backend/.venv`
- Run them with `backend/` as the working directory: `app/config.py` loads `.env` relative to the
  current working directory (known limitation, see `docs/locks/PHASE_6_6_LOCK.md`)

Each script starts with a small bootstrap that puts the backend package root on `sys.path`:

```python
# Resolve the backend package root so the script runs from any working directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

Scripts directly in `backend/scripts/` use `".."`; scripts in `manual_tests/` and `validation/` use
`"..", ".."`. This makes `import app...` work even when the script is invoked from another directory
(the `.env` requirement above still applies).

## Layout

| Path | Contents |
| --- | --- |
| `check_schema.py`, `check_schema2.py` | Inspect the remote Supabase schema and column sets; `check_schema2.py` also probes `run_sql` and dumps seeded data |
| `check_auth_users.py` | Probes `auth.users` columns/insertion and cleans up its test rows in a `finally` block |
| `debug_entries_table.py` | Checks whether the legacy `entries` table exists |
| `debug_sync.py`, `debug_sync2.py` | Trace FAQ canonical-text sync failures |
| `validation/` | Physical phase validation against a live backend: `test_physical_phase_4_2.py` (conversation/message persistence), `test_physical_phase_4_3.py` (citations and source traceability), `test_physical_phase_admin_5.py` (admin end-to-end), plus `baseline_after_live.py` and `live_conv_check.py` for latency/behaviour baselines |
| `manual_tests/` | Manual API flows: FAQ publish/delete/integration (`test_faq_*.py`, `test_faq_publish.py`), chatbot query, R2 connectivity, and an end-to-end admin suite (`end_to_end_test.py`, `test_integration.py`) |

`baseline_after_live.py` and `live_conv_check.py` import `test_physical_phase_4_2` as a sibling
module, so they must stay in the same directory (`validation/`).

## Examples

```powershell
cd backend
python scripts/check_schema.py
python scripts/validation/test_physical_phase_4_2.py
python scripts/manual_tests/end_to_end_test.py
```

Some scripts insert temporary rows into Supabase and delete them again afterwards (for example
`check_auth_users.py`). Review a script before running it against a shared database.