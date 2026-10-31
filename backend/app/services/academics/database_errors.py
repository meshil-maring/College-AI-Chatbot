"""Translate atomic Academic Setup failures without exposing database details."""

from app.core.errors import AppError


DATABASE_ERRORS = {
    "23505": (
        409, "ACADEMIC_DUPLICATE",
        "An academic record or program-course link already exists in this context",
    ),
    "23P01": (409, "ACADEMIC_DATE_CONFLICT", "Active academic year dates overlap"),
    "23514": (422, "ACADEMIC_HIERARCHY_INVALID", "Check active parents, dependent records and academic dates"),
    "23503": (422, "ACADEMIC_REFERENCE_INVALID", "An academic parent is unavailable"),
    "22003": (422, "ACADEMIC_INPUT_INVALID", "Academic numeric values exceed their supported range"),
    "22023": (422, "ACADEMIC_INPUT_INVALID", "Academic record values are invalid"),
    "P0002": (404, "ACADEMIC_NOT_FOUND", "Academic record not found"),
    "42501": (403, "FORBIDDEN", "You do not have permission to perform this action"),
}


def translate_database_error(exc: Exception) -> AppError:
    code = str(getattr(exc, "code", ""))
    if code in {"42P01", "42703", "42883", "PGRST202", "PGRST204", "PGRST205"}:
        return AppError(
            "Academic setup schema is not available. Contact your administrator.",
            503, "ACADEMIC_SCHEMA_UNAVAILABLE",
        )
    status, public_code, message = DATABASE_ERRORS.get(
        code, (500, "ACADEMIC_OPERATION_FAILED", "Academic setup operation failed")
    )
    return AppError(message, status, public_code)


def translate_deletion_error(exc: Exception, noun: str) -> AppError:
    code = str(getattr(exc, "code", ""))
    if code == "P2004":
        return AppError(
            "Select a replacement current academic year or semester before deleting this record.",
            409, "ACADEMIC_CURRENT_PERIOD",
        )
    if code in {"P2001", "P2002", "P2003", "23503"}:
        label = {
            "programs": "programs", "courses": "subjects", "semesters": "semesters",
            "program_courses": "subject mappings", "course_offerings": "course offerings",
            "program_semesters": "program semesters", "curriculum_versions": "curricula",
            "admission_cohorts": "batches", "academic_sections": "class sections",
            "academic_offerings": "subject offerings",
            "student_semester_registrations": "student assignments or registrations",
        }.get(str(getattr(exc, "details", "")), "records")
        return AppError(
            f"This {noun} cannot be deleted because it has linked {label}, "
            "including inactive records. Review its connections before closing it.",
            409, f"{noun.upper().replace(' ', '_')}_IN_USE",
        )
    return translate_database_error(exc)


