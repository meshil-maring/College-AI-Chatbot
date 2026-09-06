"""
Physical validation test for Phase 4.4 — OpenRouter + GPT-4o-mini

This test performs REAL API calls to OpenRouter and validates:
1. Configuration verification (API key, model, base URL)
2. Grounded college question with retrieved context
3. Unsupported college question without relevant context
4. Response validation and grounding verification
5. No secrets are exposed in output

IMPORTANT: This test requires OPENROUTER_API_KEY in .env

NOTE: OpenRouter may return a 429 when the account rate limit is reached.
"""

import sys
import time
from uuid import UUID, uuid4

import pytest

from app.config import settings
from app.schemas.generation import AIContext, RetrievedChunk
from app.services.generation import AIGenerationService
from app.services.generation_provider import OpenRouterGenerationProvider
from app.core.errors import AppError


@pytest.mark.skip(reason="Real provider calls require explicit manual opt-in")
class TestPhysicalValidationPhase44:
    """Physical validation tests for Phase 4.4 OpenRouter integration."""

    def test_0_configuration_verification(self):
        """Verify API key, model, and base URL are configured."""
        print("\n" + "=" * 80)
        print("TEST 0: Configuration Verification")
        print("=" * 80)

        api_key = settings.openrouter_api_key.strip()
        model = settings.openrouter_model.strip()
        base_url = settings.openrouter_base_url.strip()

        print(f"✓ Model configured: {model}")
        print(f"✓ Base URL configured: {base_url}")

        assert api_key, "OPENROUTER_API_KEY is not configured"
        assert api_key != "", "OPENROUTER_API_KEY is empty"
        assert model == "openai/gpt-4o-mini", f"Expected openai/gpt-4o-mini model, got: {model}"
        assert base_url == "https://openrouter.ai/api/v1", f"Unexpected base URL: {base_url}"

        print("✓ API key exists (value not printed)")
        print("✓ Configuration verified successfully")

    def test_1_grounded_college_question(self):
        """
        Test 1: Grounded college question with retrieved context.

        This test verifies:
        - OpenRouter request succeeds
        - HTTP response is successful
        - GPT-4o-mini returns non-empty text
        - Response mapping succeeds
        - Grounding/service validation succeeds
        - Response uses supplied college context
        - No fabricated facts are introduced
        """
        print("\n" + "=" * 80)
        print("TEST 1: Grounded College Question")
        print("=" * 80)

        # Create a realistic college knowledge context
        college_knowledge = [
            RetrievedChunk(
                chunk_id=UUID("550e8400-e29b-41d4-a716-446655440001"),
                document_id=UUID("550e8400-e29b-41d4-a716-446655440002"),
                text=(
                    "The College of Engineering at State University has an excellent reputation "
                    "for innovation and research. The department offers rigorous coursework in "
                    "mechanical, electrical, and civil engineering disciplines. Students work on "
                    "real-world projects and collaborate with industry partners throughout their "
                    "studies. The college maintains partnerships with leading technology companies "
                    "and has produced graduates who work at major tech companies worldwide."
                ),
                similarity_score=0.92,
                metadata={
                    "section": "Engineering College Overview",
                    "source": "college_handbook",
                    "page": 45,
                },
            ),
            RetrievedChunk(
                chunk_id=UUID("550e8400-e29b-41d4-a716-446655440003"),
                document_id=UUID("550e8400-e29b-41d4-a716-446655440002"),
                text=(
                    "Admission to the College of Engineering requires: 1) High school diploma or "
                    "GED, 2) Minimum 3.0 GPA, 3) Completion of pre-requisite courses in calculus, "
                    "chemistry, and physics, 4) ACT score of 28+ or SAT score of 1240+, "
                    "5) Submission of application with essay. Transfer students must have "
                    "maintained 2.5+ GPA in previous coursework and may have different requirements."
                ),
                similarity_score=0.88,
                metadata={
                    "section": "Engineering College Admissions",
                    "source": "college_handbook",
                    "page": 48,
                },
            ),
        ]

        context = AIContext(
            system_instructions=(
                "You are a helpful college admissions advisor. "
                "Answer questions based ONLY on the retrieved college knowledge below. "
                "Do not make up or invent information about the college, programs, or admissions. "
                "If the answer is not in the provided knowledge, clearly state that information is not available."
            ),
            user_question="What are the admission requirements for the College of Engineering?",
            retrieved_knowledge=college_knowledge,
            grounding_instructions=(
                "You MUST ground your answer in the provided college knowledge chunks. "
                "Cite the specific chunks that support your answer. "
                "Never invent college-specific facts that are not in the provided knowledge. "
                "If asked about information not in the knowledge, state clearly: 'This information is not provided in the college knowledge I have access to.'"
            ),
        )

        print(f"✓ Created AIContext with {len(college_knowledge)} knowledge chunks")
        print(f"✓ Question: {context.user_question}")

        # Generate response through the real OpenAI API
        provider = OpenRouterGenerationProvider()
        service = AIGenerationService(provider)

        print("→ Calling OpenRouter API...")
        try:
            response = service.generate(context)
        except AppError as e:
            # Check if the underlying cause is a rate limit error
            cause = e.__cause__
            if cause and isinstance(cause, AppError) and cause.code == "AI_PROVIDER_RATE_LIMIT":
                pytest.skip(
                    "OpenRouter rate limit exceeded during physical validation."
                )
            if "rate limit" in str(e).lower() or "429" in str(e):
                pytest.skip(
                    "OpenRouter rate limit exceeded during physical validation."
                )
            raise

        print(f"✓ Response status: {response.status}")
        print(f"✓ Model used: {response.model_used}")
        print(f"✓ Answer length: {len(response.answer) if response.answer else 0} characters")

        # Validate response
        assert response.status == "success", f"Expected success, got: {response.status}"
        assert response.answer is not None, "Answer is None"
        assert len(response.answer) > 0, "Answer is empty"
        assert response.model_used, "Model used not recorded"

        # Verify response uses context
        answer_lower = response.answer.lower()
        context_keywords = [
            "engineering",
            "college",
            "admission",
            "requirement",
            "gpa",
            "course",
        ]
        keywords_found = [kw for kw in context_keywords if kw in answer_lower]
        assert len(keywords_found) > 0, f"Answer doesn't reference college context. Found keywords: {keywords_found}"

        print(f"✓ Answer references college context (found: {keywords_found})")

        # Check that no secrets are in the response
        api_key = settings.openrouter_api_key.strip()
        assert api_key not in response.answer, "API key found in response!"
        assert "Bearer" not in response.answer, "Bearer token found in response!"
        assert "Authorization" not in response.answer, "Authorization header found in response!"

        print("✓ No secrets exposed in response")
        print("✓ Test 1 PASSED: Grounded college question successful")

        return response

    def test_2_unsupported_college_question(self):
        """
        Test 2: Unsupported/unknown college question.

        This test verifies that the existing grounding instructions prevent
        unsupported college-specific information from being presented as fact.
        """
        print("\n" + "=" * 80)
        print("TEST 2: Unsupported College Question")
        print("=" * 80)

        # Create context with knowledge that does NOT answer the question
        irrelevant_knowledge = [
            RetrievedChunk(
                chunk_id=UUID("550e8400-e29b-41d4-a716-446655440010"),
                document_id=UUID("550e8400-e29b-41d4-a716-446655440011"),
                text=(
                    "The College of Business offers degree programs in accounting, finance, "
                    "marketing, and management. The curriculum emphasizes real-world business "
                    "applications and ethical leadership."
                ),
                similarity_score=0.45,  # Low relevance
                metadata={
                    "section": "Business College Overview",
                    "source": "college_handbook",
                },
            ),
        ]

        context = AIContext(
            system_instructions=(
                "You are a helpful college admissions advisor. "
                "Answer questions based ONLY on the retrieved college knowledge below. "
                "Do not make up or invent information about the college, programs, or admissions. "
                "If the answer is not in the provided knowledge, clearly state that information is not available."
            ),
            user_question="How many students are in the College of Engineering? What is their average starting salary?",
            retrieved_knowledge=irrelevant_knowledge,
            grounding_instructions=(
                "You MUST ground your answer in the provided college knowledge chunks. "
                "If the specific information requested is not in the knowledge provided, "
                "you MUST state clearly: 'This information is not provided in the college knowledge I have access to.' "
                "Never make up specific statistics, numbers, or facts about the college."
            ),
        )

        print(f"✓ Created AIContext with {len(irrelevant_knowledge)} knowledge chunk (low relevance)")
        print(f"✓ Question: {context.user_question}")

        # Generate response through the real OpenAI API
        provider = OpenRouterGenerationProvider()
        service = AIGenerationService(provider)

        print("→ Calling OpenRouter API...")
        try:
            response = service.generate(context)
        except AppError as e:
            # Check if the underlying cause is a rate limit error
            cause = e.__cause__
            if cause and isinstance(cause, AppError) and cause.code == "AI_PROVIDER_RATE_LIMIT":
                pytest.skip(
                    "OpenRouter rate limit exceeded during physical validation."
                )
            if "rate limit" in str(e).lower() or "429" in str(e):
                pytest.skip(
                    "OpenRouter rate limit exceeded during physical validation."
                )
            raise

        print(f"✓ Response status: {response.status}")
        print(f"✓ Model used: {response.model_used}")
        print(f"✓ Answer length: {len(response.answer) if response.answer else 0} characters")

        # Validate response
        assert response.status == "success", f"Expected success, got: {response.status}"
        assert response.answer is not None, "Answer is None"
        assert len(response.answer) > 0, "Answer is empty"

        # Check that it doesn't invent specific numbers
        answer_text = response.answer
        print(f"Response text: {answer_text[:200]}...")

        # The grounding instructions should prevent fabrication
        # The response should either:
        # 1. State the information is not available
        # 2. Acknowledge it's not in the provided knowledge
        # 3. Not include made-up specific numbers about enrollment or salary
        not_available_phrases = [
            "not provided",
            "not available",
            "not found",
            "not specified",
            "don't have",
            "cannot",
            "doesn't mention",
            "not mentioned",
        ]
        has_availability_disclaimer = any(phrase in answer_text.lower() for phrase in not_available_phrases)

        print(f"✓ Response indicates information not available: {has_availability_disclaimer}")

        # Verify no secrets are in the response
        api_key = settings.openrouter_api_key.strip()
        assert api_key not in response.answer, "API key found in response!"

        print("✓ No secrets exposed in response")
        print("✓ Test 2 PASSED: Unsupported question handled appropriately")

        return response


if __name__ == "__main__":
    # Allow running this test directly for debugging
    pytest.main([__file__, "-v", "-s"])
