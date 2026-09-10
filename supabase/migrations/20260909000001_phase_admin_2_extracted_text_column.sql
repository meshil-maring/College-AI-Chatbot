-- Phase Admin-2 amendment: add missing extracted_text column to document_versions
-- The ingestion repository (store_extracted_text / get_extracted_text) references
-- this column, which was not present in the Phase 3.6 baseline.

ALTER TABLE "public"."document_versions"
    ADD COLUMN "extracted_text" "text";