"""Resolve managed study progression without rewriting student identity."""

from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.repositories.academics import academic_packages as repository
from app.services.academics.academic_packages import translate_error


def contexts(db, institution: str, rosters: list[dict]) -> dict:
    # The participation projection is present on the new authoritative roster
    # schema. Older projections continue through the strict legacy checks.
    ids = sorted({str(row['roster_id']) for row in rosters
                  if isinstance(row.get('participation_active'), bool)})
    result = {}
    for start in range(0, len(ids), 100):
        batch = ids[start:start + 100]
        try:
            data = repository.roster_context(db, institution, batch)
        except APIError as error:
            raise translate_error(error) from error
        if not isinstance(data, dict) or any(
            key not in batch or not isinstance(value, dict) for key, value in data.items()
        ):
            raise AppError("Invalid managed roster projection", 500,
                           "DATABASE_PROJECTION_INVALID")
        result.update(data)
    return result


def academic_identity(student: dict | None, roster: dict | None,
                      scope: dict, managed: dict) -> tuple[dict | None, list[str]]:
    """Only a matching explicit placement may replace admission-year context."""
    if not roster or str(roster['roster_id']) not in managed:
        return student, []
    context = managed[str(roster['roster_id'])]
    if (str(context.get('student_id') or '') != str((student or {}).get('student_id') or '')
            or any(not context.get(key) or str(context[key]) != str(scope.get(key))
                   for key in ('program_id', 'academic_year_id', 'semester_id'))):
        return student, ['Managed placement conflicts with the canonical academic identity']
    if not student:
        return None, []
    # Canonical ID, identifiers, program and account approval remain unchanged.
    return {**student, 'academic_year_id': context['academic_year_id']}, []


def first_study_semester(roster: dict | None, managed: dict, *, legacy: bool) -> bool:
    context = managed.get(str((roster or {}).get('roster_id')))
    if context is None:
        return legacy
    value = context.get('study_semester')
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 30:
        raise AppError("Invalid managed study progression", 500, "DATABASE_PROJECTION_INVALID")
    return value == 1
