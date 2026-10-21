# College AI Chatbot Backend

Follow the [backend structure rules](STRUCTURE.md) when adding or moving files.
Run `python scripts/validation/check_structure.py` from this directory to check
the layout without loading application settings or connecting to services.

## Layout

| Path | Purpose |
| --- | --- |
| `app/` | FastAPI application, repositories, schemas, middleware, configuration and security |
| `app/api/` | Routers grouped by feature; see the [API guide](app/api/README.md) |
| `app/core/` | Errors, permissions, security and startup checks; see the [core guide](app/core/README.md) |
| `app/repositories/` | Database access grouped by feature; see the [repositories guide](app/repositories/README.md) |
| `app/schemas/` | Pydantic models grouped by feature; see the [schemas guide](app/schemas/README.md) |
| `app/services/` | Services grouped by feature; see the [services guide](app/services/README.md) |
| `tests/` | Automated pytest regression suite |
| `evaluation/` | Retrieval evaluation code, dataset and evaluation reports |
| `scripts/diagnostics/` | Manual schema, authentication and FAQ sync debugging |
| `scripts/manual_tests/` | Manual API and integration checks |
| `scripts/validation/` | Live-stack phase validation |
| `scripts/generate_frontend_rbac.py` | Generate or check the frontend permission snapshot |
| `pyproject.toml`, `uv.lock`, `.python-version` | Python project definition and reproducible dependencies |
| `.env.example` | Environment configuration template |
| `../logs/backend/` | Local backend test output (ignored by Git) |

Run backend commands from this directory so settings load `backend/.env`.
See the [repository README](../README.md) for setup, startup and test commands,
and the [scripts guide](scripts/README.md) for manual tools.

## Generated files and cleanup

Keep test and diagnostic output in `../logs/backend/` instead of the backend root:

```powershell
New-Item -ItemType Directory -Force ../logs/backend | Out-Null
uv run python -m pytest tests --ignore=tests/test_physical_validation_phase_4_4.py *> ../logs/backend/pytest.log
```

Virtual environments (`.venv/`), Python bytecode (`__pycache__/`), tool caches
(`.pytest_cache/`, `.ruff_cache/`) and package metadata (`*.egg-info/`) are generated
locally and ignored by Git.

The obsolete `_wc*.py`, `_write_public_chat.py` and `fix_quotes.py` source-writing
helpers were removed after their changes were incorporated. Git history retains
them; older review evidence records their original paths and hashes.

## Historical Phase 3 Lock

Phase 3 — AI & RAG / Retrieval Foundation is now marked as:

`🔒 LOCKED`

The locked Phase 3 scope is:

- 3.1 RAG Architecture & Pipeline Contract
- 3.2 Knowledge Source & Document Model
- 3.3 Document Ingestion + Authorization
- 3.4 Text Extraction & Normalization
- 3.5 Chunking Strategy
- 3.6 Embedding Generation
- 3.7 Vector Storage & Indexing
- 3.8 Metadata & Access Filtering
- 3.9 Retrieval Pipeline
- 3.10 Retrieval Evaluation
- 3.11 Demo Knowledge Dataset
- 3.12 Validation & Phase 3 Lock

This lock preserves the existing architecture, terminology, and Phase 3 constraints. No Phase 4 functionality, no LLM generation layer, no chat frontend, and no additional retrieval enhancements are part of this lock.
