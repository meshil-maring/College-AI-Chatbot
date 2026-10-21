# Backend manual and validation scripts

Follow the shared [backend structure rules](../STRUCTURE.md).

Manual tools for debugging, API checks and "physical" validation against a live stack,
plus offline structure checks and the frontend policy generator. Run the automated suite with `pytest tests`
so these live-stack scripts are excluded from collection.

## Requirements

- Real credentials in `backend/.env` for live-stack tools (Supabase, Cloudflare R2, OpenRouter)
- A backend listening on `http://127.0.0.1:8000` for anything that calls the API
- An interpreter with the backend dependencies, e.g. `uv run python <script>` or `backend/.venv`
- Run them with `backend/` as the working directory: `app/config.py` loads `.env` relative to the
  current working directory (known limitation, see `docs/locks/PHASE_6_6_LOCK.md`)

Live-stack scripts use a small bootstrap that puts the backend package root on `sys.path`:

```python
# Resolve the backend package root so the script runs from any working directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
```

Scripts in `diagnostics/`, `manual_tests/` and `validation/` use `"..", ".."`.
This makes `import app...` work even when the script is invoked from another directory
(the `.env` requirement above still applies). `generate_frontend_rbac.py` resolves
repository source paths directly and needs no credentials or running services.
`validation/check_structure.py` also reads source directly, without importing the app.

## Layout

| Path | Contents |
| --- | --- |
| `generate_frontend_rbac.py` | Generate the typed frontend permission snapshot; `--check` verifies it without writing |
| `validation/check_structure.py` | Offline file placement, naming, package and local import checks; no settings, credentials or running services required |
| `diagnostics/check_schema.py`, `diagnostics/check_schema2.py` | Inspect the remote Supabase schema and column sets; `check_schema2.py` also probes `run_sql` and dumps seeded data |
| `diagnostics/check_auth_users.py` | Probes `auth.users` columns/insertion and cleans up its test rows in a `finally` block |
| `diagnostics/debug_entries_table.py` | Checks whether the legacy `entries` table exists |
| `diagnostics/debug_sync.py`, `diagnostics/debug_sync2.py` | Trace FAQ canonical-text sync failures |
| `validation/` | Physical phase validation against a live backend: `test_physical_phase_4_2.py` (conversation/message persistence), `test_physical_phase_4_3.py` (citations and source traceability), `test_physical_phase_admin_5.py` (admin end-to-end), `test_registration_resilience.py` (registration failure handling — a failed registration returns a controlled error and the uvicorn process keeps serving), plus `baseline_after_live.py` and `live_conv_check.py` for latency/behaviour baselines |
| `manual_tests/` | Manual API flows: FAQ publish/delete/integration (`test_faq_*.py`, `test_faq_publish.py`), chatbot query, R2 connectivity, and an end-to-end admin suite (`end_to_end_test.py`, `test_integration.py`) |

`baseline_after_live.py` and `live_conv_check.py` import `test_physical_phase_4_2` as a sibling
module, so they must stay in the same directory (`validation/`).

## Examples

```powershell
cd backend
python scripts/diagnostics/check_schema.py
python scripts/validation/test_physical_phase_4_2.py
python scripts/manual_tests/end_to_end_test.py
python scripts/generate_frontend_rbac.py --check
python scripts/validation/check_structure.py
```

Some scripts insert temporary rows into Supabase and delete them again afterwards (for example
`diagnostics/check_auth_users.py`). Review a script before running it against a shared database.

Keep local output under `logs/backend/` at the repository root. Historical review
snapshots still refer to diagnostic scripts at their former `backend/scripts/` paths.
