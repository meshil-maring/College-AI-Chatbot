"""Authorize structure operations; database RPCs enforce atomic relationships."""

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.academics import academic_structure as repository
from app.schemas.academics.academic_setup import AcademicEntity
from app.schemas.academics.academic_structure import (
    CREATE_MODELS, UPDATE_MODELS, StructureEntity, StructureResponse,
)
from app.services.academics.authorization import allowed, require, scope, validated_scope_permissions
from app.services.academics.database_errors import translate_database_error


def get_structure(user):
    institution_id, permissions = scope(user)
    if not any(allowed(permissions, entity, "read") for entity in StructureEntity):
        raise AppError("Academic structure access denied", 403, "FORBIDDEN")
    try:
        client = get_admin_client()
        permissions = validated_scope_permissions(client, user, institution_id)
        readable = [entity for entity in StructureEntity if allowed(permissions, entity, "read")]
        if not readable:
            raise AppError("Academic structure access denied", 403, "FORBIDDEN")
        records = {entity: repository.list_records(client, institution_id, entity) for entity in readable}
        activity_entities = [entity.value for entity in [*AcademicEntity, *StructureEntity]
                             if allowed(permissions, entity, "read")]
        return StructureResponse(
            institution_id=institution_id, records=records,
            manageable=[entity for entity in readable if allowed(permissions, entity, "manage")],
            activities=repository.activities(client, institution_id, activity_entities),
        )
    except AppError:
        raise
    except Exception as exc:
        raise translate_database_error(exc) from exc


def manage_record(user, entity: StructureEntity, payload, record_id=None):
    institution_id, permissions = scope(user)
    require(permissions, entity, "manage")
    model = (UPDATE_MODELS if record_id else CREATE_MODELS)[entity]
    body = model.model_validate(payload)
    fields = body.model_dump(mode="json", exclude_unset=True)
    try:
        client = get_admin_client()
        permissions = validated_scope_permissions(client, user, institution_id)
        require(permissions, entity, "manage")
        if record_id and repository.get_record(client, institution_id, entity, record_id) is None:
            raise AppError("Academic record not found", 404, "ACADEMIC_NOT_FOUND")
        row = repository.manage_record(client, str(user["user_id"]), institution_id, entity, record_id, fields)
        if (not isinstance(row, dict) or not row.get(repository.PRIMARY_KEYS[entity])
                or str(row.get("institution_id")) != institution_id):
            raise AppError("Invalid academic write response", 500, "ACADEMIC_OPERATION_FAILED")
        return row
    except AppError:
        raise
    except Exception as exc:
        raise translate_database_error(exc) from exc
