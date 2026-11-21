"""Academic eligibility assessment for student transfer requests.

Pure assessment logic: it inspects completed subjects, earned credits, subject
equivalency and the target curriculum, then recommends an eligibility status.
Final placement is always approved by authorized academic staff.
"""

from typing import Any

from app.core.errors import AppError
from app.db.supabase import get_admin_client

ELIGIBLE = "eligible"
NOT_ELIGIBLE = "not_eligible"
MANUAL_REVIEW = "manual_review"


def _row(data: Any) -> dict[str, Any] | None:
    if isinstance(data, list):
        data = data[0] if data else None
    return data if isinstance(data, dict) else None


def _first(response) -> dict[str, Any] | None:
    data = response.data
    if isinstance(data, list):
        data = data[0] if data else None
    return data if isinstance(data, dict) else None


def _completed_subjects(client, tenant: str, student_id: str) -> list[dict[str, Any]]:
    """Subjects the student has enrolled in (registered offerings)."""
    registrations = _first(
        client.table("student_semester_registrations")
        .select("semester_registration_id")
        .eq("student_id", student_id)
        .eq("institution_id", tenant)
        .execute()
    )
    reg_ids = [str(r["semester_registration_id"]) for r in (registrations or [])]
    if not reg_ids:
        return []
    response = (
        client.table("student_offering_enrollments")
        .select("subject_snapshot")
        .in_("semester_registration_id", reg_ids)
        .eq("institution_id", tenant)
        .execute()
    )
    return response.data if isinstance(response.data, list) else []


def assess_eligibility(
    client, tenant: str, request: dict[str, Any]
) -> dict[str, Any]:
    """Assess whether a transfer request is academically eligible."""
    target_program_id = request.get("target_program_id")
    target_semester_id = request.get("target_semester_id")
    target_curriculum_version_id = request.get("target_curriculum_version_id")
    student_id = str(request.get("student_id"))

    notes: list[str] = []
    missing_subjects: list[dict[str, Any]] = []

    program = _first(
        client.table("programs")
        .select("*, departments(name, code)")
        .eq("program_id", target_program_id)
        .eq("institution_id", tenant)
        .execute()
    )
    if not program or not program.get("is_active"):
        return _result(
            NOT_ELIGIBLE, "Target program is not available in this institution.", None, []
        )

    curriculum_version = None
    if target_curriculum_version_id:
        curriculum_version = _first(
            client.table("curriculum_versions")
            .select("*")
            .eq("curriculum_version_id", target_curriculum_version_id)
            .eq("program_id", target_program_id)
            .eq("institution_id", tenant)
            .eq("is_active", True)
            .execute()
        )
    if not curriculum_version:
        notes.append("No active target curriculum version resolved.")
        return _result(
            MANUAL_REVIEW,
            "; ".join(notes) or "Target curriculum could not be resolved.",
            None,
            missing_subjects,
        )

    semester = _first(
        client.table("semesters")
        .select("*")
        .eq("semester_id", target_semester_id)
        .eq("institution_id", tenant)
        .execute()
    )
    if not semester:
        return _result(
            NOT_ELIGIBLE,
            "Requested target semester does not exist in this institution.",
            None,
            missing_subjects,
        )

    target_subjects = _target_subjects(client, tenant, curriculum_version["curriculum_version_id"])
    if not target_subjects:
        notes.append("Target curriculum has no subjects defined.")
        return _result(MANUAL_REVIEW, "; ".join(notes), None, missing_subjects)

    completed = _completed_subjects(client, tenant, student_id)
    completed_names = {
        str(c.get("subject_snapshot", {}).get("name", "")).casefold() for c in completed
    }
    completed_codes = {
        str(c.get("subject_snapshot", {}).get("code", "")).casefold() for c in completed
    }
    earned_credits = sum(
        float(c.get("subject_snapshot", {}).get("credits") or 0) for c in completed
    )

    equivalencies = _equivalency_map(client, tenant, target_program_id)

    target_credits = 0.0
    for subject in target_subjects:
        target_credits += float(subject.get("credits") or 0)
        name = str(subject.get("subject_name") or "").casefold()
        code = str(subject.get("subject_code") or "").casefold()
        subjects_block = subject.get("subjects") or {}
        subject_id = str(subjects_block.get("subject_id") or "")
        covered = name in completed_names or code in completed_codes or subject_id in completed_codes
        if not covered:
            equiv = equivalencies.get(name) or equivalencies.get(code) or equivalencies.get(subject_id)
            if equiv and equiv.get("equivalence_type") in ("same", "approved_equivalent"):
                covered = True
        if not covered:
            missing_subjects.append({
                "subject_name": subject.get("subject_name"),
                "subject_code": subject.get("subject_code"),
                "credits": subject.get("credits"),
                "course_type": subject.get("course_type"),
                "is_required": subject.get("is_required"),
            })

    credit_deficit = target_credits - earned_credits
    if credit_deficit > 0:
        notes.append(
            f"Earned credits ({earned_credits}) below target curriculum credits ({target_credits})."
        )

    if missing_subjects:
        required_missing = [m for m in missing_subjects if m.get("is_required")]
        if required_missing or credit_deficit > 0:
            return _result(
                NOT_ELIGIBLE,
                "Required target subjects or credits are missing; complete them before transfer.",
                None,
                missing_subjects,
            )
        return _result(
            MANUAL_REVIEW,
            "Optional subjects missing; manual academic review recommended.",
            None,
            missing_subjects,
        )

    notes.append("Completed subjects and credits satisfy the target curriculum placement.")
    return _result(ELIGIBLE, "; ".join(notes), target_semester_id, missing_subjects)


def _result(
    status: str, notes: str, suggested_semester_id: str | None, missing: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "eligibility_status": status,
        "eligibility_notes": notes[:2000],
        "suggested_target_semester_id": suggested_semester_id,
        "missing_subjects": missing,
    }


def _target_subjects(
    client, tenant: str, curriculum_version_id: str
) -> list[dict[str, Any]]:
    response = (
        client.table("curriculum_subjects")
        .select("*, courses(name, code), subjects(name, code, credits)")
        .eq("curriculum_version_id", curriculum_version_id)
        .eq("institution_id", tenant)
        .eq("is_active", True)
        .execute()
    )
    return response.data if isinstance(response.data, list) else []


def _equivalency_map(client, tenant: str, program_id: str) -> dict[str, dict[str, Any]]:
    response = (
        client.table("subject_equivalencies")
        .select("*, subjects(name, code)")
        .eq("program_id", program_id)
        .eq("institution_id", tenant)
        .eq("is_active", True)
        .execute()
    )
    rows = response.data if isinstance(response.data, list) else []
    mapping: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in (
            str(row.get("source_subject_id")),
            str(row.get("source_subject_name") or ""),
            str(row.get("source_subject_code") or ""),
        ):
            if key:
                mapping[key.casefold()] = row
    return mapping

