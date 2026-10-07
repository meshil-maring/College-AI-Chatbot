-- Restore the reserved system parent used by public university registration.
-- This is the same seed as the existing Phase 7.13 migration, not a new tenant.
-- Existing organization settings and user/institution data are left intact.
BEGIN;
SET LOCAL lock_timeout = '10s';
SET LOCAL statement_timeout = '30s';

INSERT INTO public.organizations (
    name, organization_code, official_email, contact_information, status
) VALUES (
    'College AI Platform Institutions',
    'COLLEGE-AI-PLATFORM',
    'platform-institutions@local.invalid',
    'Reserved parent organization for institutions created through the Super Admin platform API.',
    'active'
)
ON CONFLICT (organization_code) DO NOTHING;

DO $validate$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.organizations
        WHERE organization_code = 'COLLEGE-AI-PLATFORM'
          AND status = 'active' AND join_code IS NULL
    ) THEN
        RAISE EXCEPTION 'The existing platform organization has restricted onboarding settings; review them explicitly';
    END IF;
END;
$validate$;

SELECT organization_code, status FROM public.organizations
WHERE organization_code = 'COLLEGE-AI-PLATFORM';
COMMIT;
