# Academic Setup reload repair

Date: 9 October 2026. Status: repaired and applied to the linked backend database.

After creating a program in Step 2, the catalogue started querying that program's curriculum. The live database had a legacy required `program_courses.semester_number` column and lacked the `semester_id` expected by the current backend. PostgREST returned `42703`, so the reload failed even though the program and academic year had already been saved. Migration history alone did not detect this difference from the reconstructed baseline.

`20261016010000_academic_curriculum_semester_convergence.sql` adds the nullable semester UUID and foreign key, makes the legacy number optional, preserves its existing values, and refreshes PostgREST's schema cache. The migration is idempotent. The backend also converts recognized missing academic schema errors to `503 ACADEMIC_SCHEMA_UNAVAILABLE` with a safe database-update message.

Validation:

- 69 Academic Setup API tests passed, including the missing-column failure through the catalogue query path and missing schema during writes.
- The actual migration passed PostgreSQL contracts for legacy and canonical table shapes, repeated execution, preservation of existing values, optional curriculum creation, and foreign key enforcement. Fixtures used temporary tables inside a transaction that rolled back. The contract generator is `scripts/validation/build_academic_curriculum_convergence_contract.py`.
- The deployment preview and deployment each contained only the convergence migration, with no seeds or role changes. The backend configuration and linked database target matched.
- Post-deployment checks confirmed the migration record, nullable UUID, foreign key, optional legacy number, and unchanged curriculum RLS and access protections.
- All eight backend projections and the real institution catalogue loaded successfully. The existing department, program and academic year remained present, one of each. Live verification created or updated no academic records.
- Focused fatal Ruff checks and `git diff --check` passed.

Refresh Academic Setup to continue with Step 4. The saved program and academic year do not need to be entered again.
