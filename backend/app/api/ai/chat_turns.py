"""Read-only chat recovery; generation still uses the ordinary chat endpoint."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.security import require_institution_roles, require_permission
from app.schemas.ai.chat_turns import ChatTurnStatus
from app.services.ai.turns.operations import read

router = APIRouter(prefix='/generation/turns', tags=['chat-recovery'],
    dependencies=[Depends(require_permission('ai.chat'))])
_CHAT = require_institution_roles('admin', 'faculty', 'staff', 'student')


@router.get('/{turn_id}', response_model=ChatTurnStatus)
def get_turn(turn_id: UUID, user: dict = Depends(_CHAT)):
    return read(user, turn_id)
