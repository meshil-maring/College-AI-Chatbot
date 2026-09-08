/**
 * Phase 5.5 — Demo institution configuration.
 *
 * The backend requires a scoped `institution_id` on every chat request. This
 * value is the exact, established demo institution used by every locked-phase
 * physical validation artifact in this repository:
 *
 *   - backend/test_physical_phase_4_2.py            (INSTITUTION_ID)
 *   - backend/test_physical_phase_4_3.py            (INSTITUTION_ID)
 *   - backend/tests/test_generation_api.py          (INSTITUTION_ID)
 *   - backend/tests/test_phase_4_2_persistence.py   (INSTITUTION_ID)
 *   - backend/tests/test_structured_chat_response.py (INSTITUTION_ID)
 *   - VALIDATION_REPORT_PHASE_4_4.md                 (Institution ID)
 *
 * Only one demo institution exists in the project, so this is the correct
 * identifier — it is not guessed and not invented. The frontend still never
 * validates, queries, or reasons about institutions; it only forwards this
 * constant inside the typed ChatRequest and lets the backend own institution
 * scope enforcement.
 */
export const DEMO_INSTITUTION_ID: string = '30000000-0000-0000-0000-000000000001'