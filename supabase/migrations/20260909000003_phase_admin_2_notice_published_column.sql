-- Phase Admin-2 amendment: add is_published column to notices table
-- The admin_notices service uses is_published for the RAG sync publish/unpublish flow.

ALTER TABLE "public"."notices"
    ADD COLUMN "is_published" boolean DEFAULT false NOT NULL;

CREATE INDEX IF NOT EXISTS "idx_notices_is_published"
    ON "public"."notices" ("is_published");
