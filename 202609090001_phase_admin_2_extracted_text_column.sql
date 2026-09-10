-- Phase Admin-2 amendment: add missing extracted_text column to document_versions

ALTER TABLE "public"."document_versions" ADD COLUMN "extracted_text" "text";
