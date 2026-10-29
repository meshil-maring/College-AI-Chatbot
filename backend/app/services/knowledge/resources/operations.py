"""Authorize through the atomic database writers and translate safe failures."""

from app.core.errors import AppError
from app.db.supabase import get_admin_client
from app.repositories.knowledge import resources as repository

ERRORS = {
    '40001': (409, 'RESOURCE_CHANGED', 'This resource changed. Reload before trying again.'),
    '23505': (409, 'RESOURCE_DUPLICATE', 'A duplicate resource revision or audience was submitted.'),
    '23503': (422, 'RESOURCE_REFERENCE_INVALID', 'A selected document or resource is unavailable.'),
    '23514': (422, 'RESOURCE_STATE_INVALID', 'Check the audience, review state and indexing status.'),
    '23502': (422, 'RESOURCE_FIELDS_REQUIRED', 'Complete the required resource fields.'),
    '22023': (422, 'RESOURCE_INPUT_INVALID', 'Check the submitted resource values.'),
    'P0002': (404, 'RESOURCE_NOT_FOUND', 'Resource not found.'),
    '42501': (403, 'FORBIDDEN', 'You do not have permission to perform this action.'),
}


def execute(operation, *, client=None, **parameters):
    try:
        return repository.call(client or get_admin_client(), operation, **parameters)
    except AppError:
        raise
    except Exception as failure:
        code = str(getattr(failure, 'code', ''))
        if code in {'42P01', '42703', '42883', 'PGRST202', 'PGRST204', 'PGRST205'}:
            raise AppError('The learning-resource schema is unavailable.', 503, 'RESOURCE_SCHEMA_UNAVAILABLE') from failure
        status, public_code, message = ERRORS.get(code, (500, 'RESOURCE_OPERATION_FAILED', 'The resource operation failed.'))
        raise AppError(message, status, public_code) from failure


def identity(user):
    if not user.get('user_id') or not user.get('institution_id'):
        raise AppError('Institution scope required.', 403, 'SCOPE_MISSING')
    return {'actor': str(user['user_id']), 'tenant': str(user['institution_id'])}


def save_draft(user, payload, *, source_id=None, revision_id=None, expected_version=None):
    try:
        fields = payload.database_fields()
    except ValueError as failure:
        raise AppError(str(failure), 422, 'RESOURCE_INPUT_INVALID') from failure
    return execute('save_knowledge_draft', **identity(user), payload=fields,
        source_id=str(source_id) if source_id else None,
        selected_revision=str(revision_id) if revision_id else None, expected_version=expected_version)


def revisions(user, *, revision_id=None, review=False, limit=20, offset=0):
    return execute('read_knowledge_revisions', **identity(user), mode='review' if review else 'own',
        selected_revision=str(revision_id) if revision_id else None, page_limit=limit, page_offset=offset)


def resources(user, *, source_id=None, limit=20, offset=0):
    return execute('read_knowledge_resources', **identity(user), source_id=str(source_id) if source_id else None,
        page_limit=limit, page_offset=offset)


def decide(user, revision_id, action, command):
    if action in {'publish', 'unpublish'} and command.expected_policy is None:
        raise AppError('Reload the live resource policy before publishing.', 422, 'RESOURCE_INPUT_INVALID')
    return execute('decide_knowledge_revision', **identity(user), revision=str(revision_id), action=action,
        **command.model_dump())
