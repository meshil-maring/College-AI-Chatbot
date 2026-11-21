"""Student Academic Transfer Service.

Orchestrates transfer requests: submission, eligibility assessment, review,
approval, rejection and completion. Every mutation is permission- and
tenant-checked server-side and recorded in the audit trail.
"""

from datetime import date
from typing import Any
from uuid import UUID

from app.core.errors import AppError
from app.core.security import authorize_permissions
from app.db.supabase import get_admin_client
from app.repositories.students import transfer_equivalency, transfer_placement, transfer_requests
from app.services.students.student_context import get_student_context
from app.schemas.students import transfer_request as schemas

_MISSING_SCHEMA_CODES = {"42P01", "42703", "42883", "PGRST202", "PGRST204", "PGRST205"}


def _context(actor: dict[str, Any], required: tuple[str, ...]):
    from app.services.students import transfer_util

    client, tenant_id, actor_id = transfer_util._context(actor, required)
    return client, tenant_id, actor_id



def _database(operation):
    from app.services.students import transfer_util

    return transfer_util._database(operation)



def _audit(client, tenant, actor_id, action, table_name, record_id, record_data):
    from app.services.students import transfer_util

    transfer_util._audit(client, tenant, actor_id, action, table_name, record_id, record_data)


def _actor_is_student(actor: dict[str, Any]) -> bool:
    from app.services.students import transfer_util

    return transfer_util._actor_is_student(actor)



def submit_transfer_request(
    actor: dict[str, Any],
    current_user: dict[str, Any],
    student_id: UUID,
    payload: dict[str, Any],
) -> dict[str, Any]:
    client, tenant, actor_id = _context(actor, ("transfers.request",))

    def _submit() -> dict[str, Any]:
        if _actor_is_student(actor):
            # For students, always resolve student_id from the authenticated session —
            # never trust the client-supplied value.
            context = get_student_context(current_user)
            student_id = UUID(str(context["student_id"]))
            settings = transfer_equivalency.get_transfer_settings(client, tenant=tenant)
            if not settings or not settings.get("allow_student_transfer_requests"):
                raise AppError(
                    "Student transfer requests are not enabled for this institution.",
                    403,
                    "STUDENT_TRANSFERS_DISABLED",
                )

        existing = transfer_requests.get_recent_active_request(client, student_id=student_id, tenant=tenant)
        if existing:
            raise AppError("This student already has an active transfer request.", 409, "DUPLICATE_TRANSFER_REQUEST")

        current = transfer_placement.resolve_current_placement(client, student_id=student_id, tenant=tenant)
        if not current:
            raise AppError("No current academic placement found for this student.", 400, "NO_CURRENT_PLACEMENT")

        _validate_target_placement(client, tenant, payload)

        target_section_id = payload.get("target_section_id")
        current_section = current.get("academic_sections")
        if (
            payload.get("transfer_type") == "section_transfer"
            and isinstance(current_section, dict)
            and str(current_section.get("academic_section_id")) == str(target_section_id)
        ):
            raise AppError("Target section is the same as the current section.", 422, "SAME_SECTION")

        created = transfer_requests.create_transfer_request(
            client,
            actor=actor_id,
            tenant=tenant,
            payload={
                "student_id": str(student_id),
                "transfer_type": payload["transfer_type"],
                "current_program_id": _extract_id(current, "program_id"),
                "current_batch_id": _extract_id(current, "batch_id"),
                "current_section_id": _extract_id(current, "section_id"),
                "current_semester_id": _extract_id(current, "semester_id"),
                "current_curriculum_version_id": _extract_id(current, "curriculum_version_id"),
                "target_program_id": str(payload["target_program_id"]),
                "target_batch_id": str(payload["target_batch_id"]) if payload.get("target_batch_id") else None,
                "target_section_id": str(target_section_id) if target_section_id else None,
                "target_semester_id": str(payload["target_semester_id"]) if payload.get("target_semester_id") else None,
                "target_curriculum_version_id": (
                    str(payload["target_curriculum_version_id"])
                    if payload.get("target_curriculum_version_id")
                    else None
                ),
                "reason": payload["reason"],
                "supporting_documents": payload.get("supporting_documents", []),
                "status": "submitted",
                "effective_date": str(payload["effective_date"]) if payload.get("effective_date") else None,
            },
        )
        transfer_requests.record_transfer_action(
            client,
            request_id=created["request_id"],
            tenant=tenant,
            actor=actor_id,
            action="submitted",
            from_status=None,
            to_status="submitted",
        )
        _audit(
            client, tenant, actor_id, "transfer_requests.create", "transfer_requests",
            created["request_id"], {"status": "submitted", "transfer_type": payload["transfer_type"]},
        )
        return get_transfer_request_view(actor, created["request_id"])

    return _database(_submit)


def _extract_id(placement: dict[str, Any] | None, key: str) -> str | None:
    if not placement:
        return None
    value = placement.get(key)
    if value is not None:
        return str(value)
    for nest_key in ("academic_sections", "admission_cohorts", "academic_batches", "program_semesters", "semesters"):
        nest = placement.get(nest_key)
        if isinstance(nest, dict) and nest.get(key) is not None:
            return str(nest[key])
    return None


def _validate_target_placement(client: Any, tenant: Any, payload: dict[str, Any]) -> None:
    program_id = str(payload["target_program_id"])
    program = client.table("programs").select("*, departments(name, code)").eq("program_id", program_id).eq("institution_id", str(tenant)).maybe_single().execute()
    program_row = program.data if isinstance(program.data, dict) else None
    if not program_row or not program_row.get("is_active"):
        raise AppError("Target program is not available in this institution.", 422, "TARGET_PROGRAM_UNAVAILABLE")

    def _check(table: str, id_column: str, value: str | None, label: str) -> None:
        if not value:
            return
        row = (
            client.table(table)
            .select(id_column)
            .eq(id_column, value)
            .eq("program_id", program_id)
            .eq("institution_id", str(tenant))
            .maybe_single()
            .execute()
        )
        data = row.data
        if isinstance(data, list):
            data = data[0] if data else None
        if not data:
            raise AppError(f"Target {label} does not belong to the target program.", 422, "TARGET_TARGET_INVALID")

    _check("academic_batches", "batch_id", payload.get("target_batch_id"), "batch")
    _check("academic_sections", "academic_section_id", payload.get("target_section_id"), "section")
    _check("semesters", "semester_id", payload.get("target_semester_id"), "semester")
    _check("curriculum_versions", "curriculum_version_id", payload.get("target_curriculum_version_id"), "curriculum version")


def get_transfer_request(actor: dict[str, Any], request_id: UUID) -> dict[str, Any]:
    client, tenant, actor_id = _context(actor, ("transfers.read",))
    return _database(lambda: _get(client, tenant, actor_id, str(request_id)))


def _get(client: Any, tenant: Any, actor_id: str, request_id: str) -> dict[str, Any]:
    request = transfer_requests.get_transfer_request(client, request_id=request_id, tenant=tenant)
    if not request:
        raise AppError("Transfer request not found.", 404, "TRANSFER_REQUEST_NOT_FOUND")
    return request


def list_transfer_requests(
    actor: dict[str, Any],
    student_id: UUID | None = None,
    status: str | None = None,
    transfer_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    client, tenant, actor_id = _context(actor, ("transfers.read",))

    def _list() -> dict[str, Any]:
        result = transfer_requests.list_transfer_requests(
            client, tenant=tenant, student_id=student_id, status=status,
            transfer_type=transfer_type, limit=limit, offset=offset,
        )
        # Map created_at → submitted_at to satisfy the TransferRequestListItem schema
        items = [
            {**row, "submitted_at": str(row["created_at"]) if row.get("created_at") else ""}
            for row in result.get("items", [])
        ]
        return {**result, "items": items}

    return _database(_list)


def _build_placement(row: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Extract a flat AcademicPlacement dict from a transfer_requests row using a field prefix."""
    return {
        "program_id": row.get(f"{prefix}_program_id"),
        "program_name": None,
        "program_code": None,
        "batch_id": row.get(f"{prefix}_batch_id"),
        "batch_name": None,
        "batch_code": None,
        "section_id": row.get(f"{prefix}_section_id"),
        "section_name": None,
        "section_code": None,
        "semester_id": row.get(f"{prefix}_semester_id"),
        "semester_name": None,
        "curriculum_version_id": row.get(f"{prefix}_curriculum_version_id"),
        "curriculum_version": None,
        "effective_from": None,
        "effective_to": None,
        "is_active": None,
    }


def get_transfer_request_view(actor: dict[str, Any], request_id: UUID) -> dict[str, Any]:
    client, tenant, actor_id = _context(actor, ("transfers.read",))
    request = transfer_requests.get_transfer_request(client, request_id=str(request_id), tenant=tenant)
    if not request:
        raise AppError("Transfer request not found.", 404, "TRANSFER_REQUEST_NOT_FOUND")
    actions = (
        client.table("transfer_request_actions")
        .select("*")
        .eq("request_id", str(request_id))
        .eq("institution_id", str(tenant))
        .order("created_at", desc=False)
        .execute()
    )
    action_rows = actions.data if isinstance(actions.data, list) else []
    request_view = {
        **request,
        "current_placement": _build_placement(request, "current"),
        "target_placement": _build_placement(request, "target"),
        "created_at": str(request["created_at"]) if request.get("created_at") else "",
        "updated_at": str(request["updated_at"]) if request.get("updated_at") else "",
    }
    return {
        "request": request_view,
        "actions": [
            {
                "action_id": a.get("action_id"),
                "action": a.get("action"),
                "actor_user_id": a.get("actor_user_id"),
                "comments": a.get("comments"),
                "from_status": a.get("from_status"),
                "to_status": a.get("to_status"),
                "created_at": str(a.get("created_at")) if a.get("created_at") else None,
            }
            for a in action_rows
        ],
    }





