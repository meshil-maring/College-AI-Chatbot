"""Assessment routes use the established authenticated Faculty dependency."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.security import require_institution_roles
from app.schemas.faculty_tests import (
    Correction,
    ImportCommit,
    ImportCorrection,
    MarksCommand,
    TestInput,
    TestUpdate,
    Transition,
)
from app.services import faculty_tests as service
from app.services.faculty_attendance import MAX_IMPORT_BYTES
from app.services.ingestion import read_upload_limited

router = APIRouter(prefix='/tests', tags=['faculty tests'])
faculty = require_institution_roles('faculty')


@router.get('/resources')
def resources(user: dict = Depends(faculty)):
    return service.resources(user)


@router.get('/types')
def types(user: dict = Depends(faculty)):
    return service.types(user)


@router.get('/sections/{section_id}')
def tests(section_id: UUID, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=500), user: dict = Depends(faculty)):
    return service.list_tests(user, section_id, offset=offset, limit=limit)


@router.post('/sections/{section_id}', status_code=201)
def create(section_id: UUID, payload: TestInput, user: dict = Depends(faculty)):
    return service.save_test(user, section_id, payload)


@router.get('/imports/{import_id}')
def review(import_id: UUID, user: dict = Depends(faculty)):
    return service.review_import(user, import_id)


@router.patch('/imports/{import_id}/rows/{number}')
def correct_import(import_id: UUID, number: int, payload: ImportCorrection, user: dict = Depends(faculty)):
    return service.correct_import(user, import_id, number, payload)


@router.post('/imports/{import_id}/commit')
def commit(import_id: UUID, payload: ImportCommit, user: dict = Depends(faculty)):
    return service.commit_import(user, import_id, payload)


@router.get('/{test_id}')
def detail(test_id: UUID, user: dict = Depends(faculty)):
    return service.marks(user, test_id)


@router.patch('/{test_id}')
def update(test_id: UUID, payload: TestUpdate, user: dict = Depends(faculty)):
    t = service.test_row(user, test_id, manage=True)
    return service.save_test(user, UUID(t['section_id']), payload, test_id)


@router.post('/{test_id}/transition')
def transition(test_id: UUID, payload: Transition, user: dict = Depends(faculty)):
    return service.transition(user, test_id, payload)


@router.put('/{test_id}/marks')
def marks(test_id: UUID, payload: MarksCommand, user: dict = Depends(faculty)):
    return service.save_marks(user, test_id, payload)


@router.post('/{test_id}/corrections')
def correction(test_id: UUID, payload: Correction, user: dict = Depends(faculty)):
    return service.save_marks(user, test_id, payload, correction=True)


@router.post('/{test_id}/imports', status_code=201)
async def upload(test_id: UUID, file: UploadFile = File(...), user: dict = Depends(faculty)):
    await run_in_threadpool(service.test_row, user, test_id, manage=True)
    content = await read_upload_limited(file, MAX_IMPORT_BYTES)
    return await run_in_threadpool(service.upload_import, user, test_id, file.filename or '', content, file.content_type)


@router.get('/{test_id}/history')
def history(test_id: UUID, user: dict = Depends(faculty)):
    return service.history(user, test_id)
