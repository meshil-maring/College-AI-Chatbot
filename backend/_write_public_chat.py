import textwrap

content = r'''"""Phase 6.13 — Public (unauthenticated) chat endpoint service.

Mirrors app.services.chat.process_chat_request so that public conversations
reuse the same chat boundary, turn/conversation ownership model, bounded
history, query rewriting, retrieval, generation, and citation pipeline —
EXCEPT:

1. user_id is always PUBLIC_USER_ID (a constant, never derived from a JWT).
2. Personalization is never loaded (no current_user → no student context).
3. institution_id is accepted for forward-compatibility but is not required
   and does not participate in any tenant-scoped authorization check.
"""

from __future__ import annotations

import re
import threading
import time
from uuid import UUID

from app.config import settings
from app.core.security import PUBLIC_USER_ID
from app.db.supabase import get_admin_client
from app.repositories.ai_response import create_ai_response
from app.repositories.conversation import (
    create_conversation,
    get_conversation,
    update_conversation_timestamp,
)
from app.repositories.message import create_message, get_next_message_sequence
from app.repositories.message_citation import create_message_citations
from app.repositories.retrieval_operation import (
    create_retrieval_operation,
    create_retrieved_chunks,
)
from app.schemas.citation import (
    MessageCitationCreate,
    RetrievedChunkCreate,
    RetrievalOperationCreate,
)
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.chat_response import ChatUsage, StructuredSource
from app.schemas.conversation import (
    AIResponseCreate,
    ConversationCreate,
    MessageCreate,
)
from app.schemas.generation import (
    AIRequest,
    ConversationTurn,
    RetrievalScope,
    RetrievedChunk,
    SourceReference,
)
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalResult
from app.schemas.session import SessionContext
from app.services.conversation_history import get_conversation_messages
from app.services.generation import AIGenerationService
from app.services.generation_provider import GenerationProvider
from app.services.retrieval import retrieve

PROCESS_CHAT_REQUEST = "app.services.public_chat.process_chat_request"

__all__ = ["process_chat_request"]
'''

with open('app/services/public_chat.py', 'w') as f:
    f.write(content)
print('Header written')
