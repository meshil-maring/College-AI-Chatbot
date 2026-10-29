"""Answer layout survives model validation, generation and HTTP projection."""

import pytest

from app.schemas.ai.generation import AIContext, AIResponse, RetrievedChunk
from app.schemas.ai.chat import PublicChatResponse
from app.services.ai.generation import AIGenerationService
from app.services.ai.generation_provider import GenerationResult


ANSWER = (
    'This document is a **draft sample**.\n\n'
    '### Hostel rules\n\n'
    '1. **Room allocation**\n'
    '   - Obtain approval before changing rooms.\n'
    '2. **Visitors**\n'
    '   - Overnight guests need permission.\n\n'
    '```text\n'
    '  Keep this indentation.\n'
    '```'
)


@pytest.mark.parametrize('text', [ANSWER, ANSWER.replace('\n', '\r\n'), ANSWER.replace('\n', '\r')])
def test_multiline_markdown_and_indentation_are_preserved(text):
    result = AIResponse(answer='\n' + text + '\n', status='success')
    assert result.answer == ANSWER
    assert result.model_dump()['answer'] == ANSWER


def test_blank_answers_remain_invalid():
    with pytest.raises(ValueError, match='answer must not be empty'):
        AIResponse(answer=' \n\t\r\n ', status='success')


def test_single_line_normalization_remains_compatible():
    assert AIResponse(answer='  Short   answer.  ').answer == 'Short answer.'


def test_provider_layout_reaches_public_response_unchanged():
    class Provider:
        def generate(self, context):
            return GenerationResult(answer=ANSWER, status='success')

    context = AIContext(system_instructions='Use the source.', user_question='Hostel rules?',
        retrieved_knowledge=[RetrievedChunk(chunk_id='00000000-0000-0000-0000-000000000001',
            text='Room changes and guests require permission.', similarity_score=0.9)])
    generated = AIGenerationService(Provider()).generate(context)
    public = PublicChatResponse(answer=generated.answer, status=generated.status)
    assert public.model_dump()['answer'] == ANSWER
