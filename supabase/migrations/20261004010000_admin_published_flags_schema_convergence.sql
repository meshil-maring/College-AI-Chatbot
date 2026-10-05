-- Repair environments where the original Admin-2 publication migrations were
-- recorded as applied without their schema changes being present.

ALTER TABLE "public"."faqs"
    ADD COLUMN IF NOT EXISTS "is_published" boolean DEFAULT false NOT NULL;

CREATE INDEX IF NOT EXISTS "idx_faqs_is_published"
    ON "public"."faqs" ("is_published");

ALTER TABLE "public"."notices"
    ADD COLUMN IF NOT EXISTS "is_published" boolean DEFAULT false NOT NULL;

CREATE INDEX IF NOT EXISTS "idx_notices_is_published"
    ON "public"."notices" ("is_published");

NOTIFY pgrst, 'reload schema';
