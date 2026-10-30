# Local semester registration validation

Run from the repository root:

```powershell
python scripts/validation/semester_registration/run.py
```

The runner reuses the existing disposable PostgreSQL ownership checks and image.
It never uses application database credentials or contacts a hosted project.
It replays all migrations, seeds fictional Academic Setup data, then tests the
eight-subject Semester 3 scenario with two required subjects and two alternatives.

Contracts cover tenant and student ownership, exactly one option, five subject
enrollments for either alternative, missing offerings, rollback, subject capacity,
idempotent retries, published option immutability and historical credit snapshots.
Logs belong in `logs/backend/`.
