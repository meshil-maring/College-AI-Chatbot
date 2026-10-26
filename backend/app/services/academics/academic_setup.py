"""Coordinate academic foundation authorization, validation and persistence."""

from pydantic import ValidationError

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.academics import academic_setup as repository
from app.services.academics.parent_validation import validate_structure_parents
from app.services.academics.authorization import allowed, require, scope, validated_scope_permissions
from app.services.academics.database_errors import translate_database_error
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
