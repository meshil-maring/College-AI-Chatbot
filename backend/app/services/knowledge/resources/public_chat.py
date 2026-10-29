"""Recheck public eligibility around the established stateless public processor."""

from app.core.errors import AppError
from app.services.ai import public_chat as processor
from httpx import TransportError
from .operations import execute


def _snapshot(institution_code):
    try:
        return execute('snapshot_public_knowledge_policy', institution_code=institution_code)
    except AppError as failure:
        if failure.status_code == 404:
            raise AppError('Institution not found', 404, 'INSTITUTION_NOT_FOUND') from failure
        if isinstance(failure.__cause__, TransportError):
            raise AppError('The chatbot is temporarily unavailable. Please try again shortly.',
                503, 'PUBLIC_CHAT_UNAVAILABLE', headers={'Retry-After': '5'}) from failure
        raise


def process_public_request(request, context, provider):
    # A conservative corpus snapshot also covers removal of a canonical FAQ's
    # last published file. No source IDs or fingerprints enter the public reply.
    before = _snapshot(request.institution_code)
    response = processor.process_public_request(request, context, provider)
    after = _snapshot(request.institution_code)
    if before != after:
        raise AppError('Public knowledge changed while preparing the answer. Please ask again.',
            409, 'RESOURCE_CHANGED')
    return response
