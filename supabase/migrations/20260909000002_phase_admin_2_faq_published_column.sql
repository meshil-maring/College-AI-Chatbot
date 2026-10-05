-- Phase Admin-2 amendment: add is_published column to faqs table
-- The admin_faq service uses is_published for the RAG sync publish/unpublish flow.

ALTER TABLE "public"."faqs"
    ADD COLUMN "is_published" boolean DEFAULT false NOT NULL;

CREATE INDEX IF NOT EXISTS "idx_faqs_is_published"
    ON "public"."faqs" ("is_published");
