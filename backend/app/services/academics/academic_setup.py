"""Coordinate academic foundation authorization, validation and persistence."""

from pydantic import ValidationError

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.academics import academic_setup as repository
from app.services.academics.parent_validation import validate_structure_parents
from app.services.academics.authorization import allowed, require, scope, validated_scope_permissions
from app.services.academics.database_errors import translate_database_error, translate_deletion_error
from app.schemas.academics.academic_setup import (
    AcademicEntity,
    AcademicSetupResponse,
    CREATE_MODELS,
    UPDATE_MODELS,
)


def get_setup(user) -> AcademicSetupResponse:
    institution_id, permissions = scope(user)
    readable = [entity for entity in AcademicEntity if allowed(permissions, entity, "read")]
    if not readable:
        raise AppError("Academic setup access denied", 403, "FORBIDDEN")
    try:
        client = get_admin_client()
        permissions = validated_scope_permissions(client, user, institution_id)
        readable = [entity for entity in AcademicEntity if allowed(permissions, entity, "read")]
        if not readable:
            raise AppError("Academic setup access denied", 403, "FORBIDDEN")
        records = {
            entity: repository.list_records(client, institution_id, entity)
            for entity in readable
        }
    except AppError:
        raise
    except Exception as exc:
        raise translate_database_error(exc) from exc
    return AcademicSetupResponse(
        institution_id=institution_id,
        records=records,
        manageable=[entity for entity in readable if allowed(permissions, entity, "manage")],
    )


def manage_record(user, entity: AcademicEntity, payload, record_id=None) -> dict:
    institution_id, permissions = scope(user)
    require(permissions, entity, "manage")
    model = (UPDATE_MODELS if record_id else CREATE_MODELS)[entity]
    body = model.model_validate(payload)
    fields = body.model_dump(mode="json", exclude_unset=True)
    try:
        client = get_admin_client()
        permissions = validated_scope_permissions(client, user, institution_id)
        require(permissions, entity, "manage")
        existing = None
        if record_id:
            existing = repository.get_record(client, institution_id, entity, record_id)
            if existing is None:
                raise AppError("Academic record not found", 404, "ACADEMIC_NOT_FOUND")
            if entity in {AcademicEntity.academic_years, AcademicEntity.semesters}:
                # Validate partial date/current changes against persisted values.
                combined = {key: existing[key] for key in CREATE_MODELS[entity].model_fields}
                CREATE_MODELS[entity].model_validate({**combined, **fields})
        validate_structure_parents(client, institution_id, entity, fields, existing)
        row = repository.manage_record(
            client, str(user["user_id"]), institution_id, entity, record_id, fields
        )
        if not isinstance(row, dict) or row.get(repository.PRIMARY_KEYS[entity]) is None:
            raise AppError("Invalid academic write response", 500, "ACADEMIC_OPERATION_FAILED")
        if "institution_id" in row and str(row["institution_id"]) != institution_id:
            raise AppError("Invalid academic write response", 500, "ACADEMIC_OPERATION_FAILED")
        return {**row, "institution_id": institution_id}
    except (AppError, ValidationError):
        raise
    except Exception as exc:
        raise translate_database_error(exc) from exc


def delete_department(user, department_id: str) -> dict:
    return _delete_unused_record(user, AcademicEntity.departments, department_id)


def delete_program(user, program_id: str) -> dict:
    return _delete_unused_record(user, AcademicEntity.programs, program_id)


def delete_period(user, entity: AcademicEntity, record_id: str) -> dict:
    if entity not in {AcademicEntity.academic_years, AcademicEntity.semesters}:
        raise AppError("Unsupported calendar entity", 422, "ACADEMIC_INPUT_INVALID")
    return _delete_unused_record(user, entity, record_id)


def _delete_unused_record(user, entity: AcademicEntity, record_id: str) -> dict:
    noun = {
        AcademicEntity.departments: "department", AcademicEntity.programs: "program",
        AcademicEntity.academic_years: "academic year", AcademicEntity.semesters: "semester",
    }[entity]
    institution_id, permissions = scope(user)
    require(permissions, entity, "manage")
    try:
        client = get_admin_client()
        permissions = validated_scope_permissions(client, user, institution_id)
        require(permissions, entity, "manage")
        existing = repository.get_record(client, institution_id, entity, record_id)
        if existing is None:
            raise AppError("Academic record not found", 404, "ACADEMIC_NOT_FOUND")
        if entity in {AcademicEntity.academic_years, AcademicEntity.semesters}:
            if existing.get("is_current") is True:
                raise AppError(
                    "Select a replacement current academic year or semester before deleting this record.",
                    409, "ACADEMIC_CURRENT_PERIOD",
                )
            row = repository.delete_period(client, str(user["user_id"]), institution_id, entity, record_id)
        else:
            writer = repository.delete_department if entity == AcademicEntity.departments else repository.delete_program
            row = writer(client, str(user["user_id"]), institution_id, record_id)
        if (
            not isinstance(row, dict) or str(row.get(repository.PRIMARY_KEYS[entity])) != record_id
            or str(row.get("institution_id")) != institution_id
        ):
            raise AppError(f"Invalid {noun} deletion response", 500, "ACADEMIC_OPERATION_FAILED")
        return row
    except AppError:
        raise
    except Exception as exc:
        raise translate_deletion_error(exc, noun) from exc
