#!/usr/bin/env python
"""Phase 4.4 FINAL PHYSICAL VALIDATION — End-to-end generation path test.

This is a REAL, grounded test using:
- Real college knowledge from the evaluation dataset
- Real AIContext and AIGenerationService
- Real OpenRouter API with openai/gpt-4o-mini
- Real source reference extraction and grounding validation

No temporary endpoints or mocks for the OpenRouter call.
"""

import json
import sys
import time
from uuid import UUID
from pathlib import Path

# Add backend to path so we can import the app
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.schemas.generation import AIContext, RetrievedChunk
from app.services.generation import AIGenerationService
from app.services.generation_provider import OpenRouterGenerationProvider

# Test setup with known UUIDs from evaluation dataset
INSTITUTION_ID = "30000000-0000-0000-0000-000000000001"
CHUNK_EXAM_ATTENDANCE = UUID("30000000-0000-0000-0000-000000000151")

BACKEND_URL = "http://localhost:8000/api/v1"
TIMEOUT = 90.0


def main():
    print("\n" + "=" * 80)
    print("COLLEGE AI CHATBOT — PHASE 4.4")
    print("FINAL PHYSICAL VALIDATION")
    print("=" * 80)
    print(f"\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"Configuration:")
    print(f"  Provider: OpenRouter")
    print(f"  Model: {settings.openrouter_model}")
    print(f"  Base URL: {settings.openrouter_base_url}")
    print(f"  API Key configured: {'YES' if settings.openrouter_api_key else 'NO'}")
    
    # VALIDATION 1: GROUNDED QUESTION
    print("\n" + "=" * 80)
    print("VALIDATION 1: GROUNDED QUESTION")
    print("=" * 80)
    
    question = "What attendance level do I need in a course to be allowed to take the regular end-semester exam?"
    
    # The chunk that answers this question
    chunk = RetrievedChunk(
        chunk_id=CHUNK_EXAM_ATTENDANCE,
        text="A minimum attendance of 75% is mandatory for eligibility to take the regular end-semester examination.",
        similarity_score=0.95,
        metadata={
            "section": "Attendance Requirements",
            "chunk_sequence": 1,
            "model_name": "qwen/qwen3-embedding-8b",
            "document_id": "30000000-0000-0000-0000-000000000121",
        },
    )
    
    print(f"\nQuestion: {question}")
    print(f"Retrieved Chunks: 1")
    print(f"  Chunk ID: {CHUNK_EXAM_ATTENDANCE}")
    print(f"  Chunk text: {chunk.text[:80]}...")
    print(f"  Similarity: {chunk.similarity_score}")
    
    # Build AIContext for the grounded question
    context = AIContext(
        system_instructions="You are a college student information assistant. Answer questions using only the provided college knowledge.",
        user_question=question,
        retrieved_knowledge=[chunk],
        grounding_instructions="When referencing college knowledge, include the chunk ID in parentheses like this: (source: chunk {chunk_id}). Never invent facts not in the provided chunks.",
        model_name=settings.openrouter_model,
    )
    
    print(f"\nCalling AIGenerationService with real OpenRouter provider...")
    print(f"  Model: {context.model_name}")
    print(f"  Context type: {type(context).__name__}")
    print(f"  Retrieved knowledge count: {len(context.retrieved_knowledge)}")
    
    # Create provider and service
    provider = OpenRouterGenerationProvider(timeout=TIMEOUT)
    service = AIGenerationService(provider)
    
    # Execute the real generation request
    try:
        start_time = time.time()
        response = service.generate(context)
        elapsed = time.time() - start_time
        
        print(f"\n✓ Generation completed in {elapsed:.2f}s")
        print(f"\nResponse Details:")
        print(f"  Status: {response.status}")
        print(f"  Model used: {response.model_used}")
        print(f"  Provider: {response.metadata.get('provider', 'N/A')}")
        
        if response.answer:
            print(f"  Answer (first 150 chars): {response.answer[:150]}...")
            print(f"  Full answer length: {len(response.answer)} chars")
        else:
            print(f"  Answer: (None)")
        
        print(f"\nSource References: {len(response.source_references)}")
        grounding_verified = False
        
        for i, ref in enumerate(response.source_references):
            print(f"  Reference {i+1}:")
            print(f"    Chunk ID: {ref.chunk_id}")
            if ref.chunk_id == CHUNK_EXAM_ATTENDANCE:
                grounding_verified = True
                print(f"    ✓ MATCHES expected chunk")
            print(f"    Quote: {ref.quote[:80]}...")
        
        # Verify grounding
        print(f"\nGrounding Verification:")
        print(f"  Expected chunk: {CHUNK_EXAM_ATTENDANCE}")
        print(f"  Found in sources: {grounding_verified}")
        
        # Metadata
        if response.metadata:
            print(f"\nMetadata:")
            for key, value in response.metadata.items():
                if key not in ['provider']:
                    print(f"  {key}: {value}")
        
        # Determine validation result
        validation_pass = (
            response.status == "success"
            and response.answer is not None
            and len(response.answer) > 0
            and response.model_used == settings.openrouter_model
            and grounding_verified
        )
        
        if validation_pass:
            print(f"\n✓ VALIDATION 1 PASSED")
            print(f"  ✓ Real OpenRouter request succeeded")
            print(f"  ✓ Model is correct: {response.model_used}")
            print(f"  ✓ Answer is grounded in retrieved chunk")
            print(f"  ✓ Source reference is honest and verified")
            return True, {
                "status": "PASS",
                "elapsed_seconds": elapsed,
                "model": response.model_used,
                "provider": response.metadata.get('provider'),
                "answer": response.answer,
                "source_references": len(response.source_references),
                "grounding_verified": grounding_verified,
                "retrieved_chunk_count": len(context.retrieved_knowledge),
                "response_status": response.status,
            }
        else:
            print(f"\n✗ VALIDATION 1 FAILED")
            print(f"  Status: {response.status}")
            print(f"  Model correct: {response.model_used == settings.openrouter_model}")
            print(f"  Has answer: {bool(response.answer)}")
            print(f"  Grounding verified: {grounding_verified}")
            return False, {
                "status": "FAIL",
                "reason": "Validation criteria not met",
                "response_status": response.status,
            }
            
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"\n✗ Exception during generation: {e}")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, {
            "status": "FAIL",
            "error": str(e),
            "elapsed_seconds": elapsed,
        }


if __name__ == "__main__":
    success, result = main()
    
    # Print final report
    print("\n" + "=" * 80)
    print("FINAL RESULT")
    print("=" * 80)
    
    if success:
        print("\n✓ PHASE 4.4 PHYSICAL VALIDATION: PASSED")
        print(f"\nResult details:")
        for key, value in result.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
    else:
        print("\n✗ PHASE 4.4 PHYSICAL VALIDATION: FAILED")
        print(f"\nFailure details:")
        for key, value in result.items():
            print(f"  {key}: {value}")
    
    sys.exit(0 if success else 1)
