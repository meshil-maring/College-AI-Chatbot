-- Employee profiles for institution Staff and Faculty (User Management U1, U3, U4).
--
-- One person keeps one login identity (public.users). Each institution keeps its
-- own employee record for that person: a common profile shared by every member
-- type, and a Faculty or Staff profile for the role-specific details. Existing
-- members have no profile until an administrator completes it, so every profile
-- column that the form requires is NOT NULL inside its row.
--
-- The primary department stays in institution_member_departments (one row per
-- member). Further departments are kept in institution_member_additional_departments.
-- Department association never grants teaching access by itself.
--
-- Account access is still decided by public.users.status, which every sign-in
-- check and permission function compares with 'active'. 'suspended' is added so
-- an administrator can pause access without deactivating the account.
-- Employment status is derived from the contract end date and is not stored.
--
-- Only the backend service role reads or writes these tables; the commands in
-- 20261128010000 check the administrator and the member before every write.
BEGIN;

ALTER TABLE public.users DROP CONSTRAINT users_status_check;
ALTER TABLE public.users ADD CONSTRAINT users_status_check
    CHECK (status = ANY (ARRAY['active', 'inactive', 'suspended', 'deactivated']));

CREATE TABLE public.institution_member_profiles (
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    employee_id text NOT NULL
        CHECK (length(btrim(employee_id)) BETWEEN 1 AND 40
               AND employee_id ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'),
    phone text CHECK (phone IS NULL OR phone ~ '^\+?[0-9][0-9 ()-]{4,30}$'),
    designation text NOT NULL CHECK (length(btrim(designation)) BETWEEN 1 AND 120),
    joining_date date NOT NULL,
    created_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (institution_id, user_id)
);

-- Employee IDs are unique within an institution, ignoring case.
CREATE UNIQUE INDEX institution_member_profiles_employee_id
    ON public.institution_member_profiles (institution_id, lower(employee_id));

-- Faculty employment types. A contract end date is required unless permanent.
CREATE TABLE public.faculty_profiles (
    institution_id uuid NOT NULL,
    user_id uuid NOT NULL,
    qualification text CHECK (qualification IS NULL OR length(btrim(qualification)) BETWEEN 1 AND 200),
    specialization text CHECK (specialization IS NULL OR length(btrim(specialization)) BETWEEN 1 AND 200),
    experience_years numeric(4, 1) CHECK (experience_years IS NULL OR experience_years BETWEEN 0 AND 70),
    employment_type text NOT NULL
        CHECK (employment_type IN ('permanent', 'temporary', 'contractual', 'visiting', 'guest')),
    employment_start_date date NOT NULL,
    contract_end_date date,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (institution_id, user_id),
    FOREIGN KEY (institution_id, user_id)
        REFERENCES public.institution_member_profiles (institution_id, user_id) ON DELETE CASCADE,
    CONSTRAINT faculty_profiles_contract_end
        CHECK ((employment_type = 'permanent') OR contract_end_date IS NOT NULL),
    CONSTRAINT faculty_profiles_contract_order
        CHECK (contract_end_date IS NULL OR contract_end_date >= employment_start_date)
);

CREATE TABLE public.staff_profiles (
    institution_id uuid NOT NULL,
    user_id uuid NOT NULL,
    staff_category text NOT NULL CHECK (staff_category IN (
        'office_administration', 'accounts_finance', 'library', 'it_support',
        'laboratory', 'hostel_administration', 'examination_office', 'other'
    )),
    employment_type text NOT NULL CHECK (employment_type IN ('permanent', 'temporary', 'contractual')),
    employment_start_date date NOT NULL,
    contract_end_date date,
    -- Institution-defined job responsibilities, chosen or typed by the administrator.
    responsibilities text[] NOT NULL
        CHECK (cardinality(responsibilities) BETWEEN 1 AND 20
               AND array_position(responsibilities, NULL) IS NULL),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (institution_id, user_id),
    FOREIGN KEY (institution_id, user_id)
        REFERENCES public.institution_member_profiles (institution_id, user_id) ON DELETE CASCADE,
    CONSTRAINT staff_profiles_contract_end
        CHECK ((employment_type = 'permanent') OR contract_end_date IS NOT NULL),
    CONSTRAINT staff_profiles_contract_order
        CHECK (contract_end_date IS NULL OR contract_end_date >= employment_start_date)
);

CREATE TABLE public.institution_member_additional_departments (
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    -- RESTRICT keeps a department in use from being deleted, like the primary one.
    department_id uuid NOT NULL REFERENCES public.departments(department_id) ON DELETE RESTRICT,
    assigned_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    assigned_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (institution_id, user_id, department_id)
);

CREATE INDEX institution_member_additional_departments_department
    ON public.institution_member_additional_departments (department_id);

-- The department must belong to the member's institution (same rule as primary).
CREATE TRIGGER institution_member_additional_departments_same_tenant
    BEFORE INSERT OR UPDATE ON public.institution_member_additional_departments
    FOR EACH ROW EXECUTE FUNCTION public.institution_member_departments_same_tenant();

DO $$
DECLARE relation_name text;
BEGIN
    FOREACH relation_name IN ARRAY ARRAY['institution_member_profiles', 'faculty_profiles',
        'staff_profiles', 'institution_member_additional_departments'] LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', relation_name);
        -- Writes go only through the audited commands; the service role reads.
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC, anon, authenticated, service_role',
            relation_name);
        EXECUTE format('GRANT SELECT ON TABLE public.%I TO service_role', relation_name);
    END LOOP;
END;
$$;

-- An administrator's invitation may carry the profile the administrator entered.
-- It is applied when the person accepts and, like the other details, is immutable.
ALTER TABLE public.platform_admin_invitations
    ADD COLUMN invited_profile jsonb,
    ADD CONSTRAINT platform_admin_invitations_invited_profile_check
        CHECK (invited_profile IS NULL
               OR (admin_invited AND jsonb_typeof(invited_profile) = 'object'));

CREATE OR REPLACE FUNCTION public.member_invitation_details_immutable()
RETURNS trigger LANGUAGE plpgsql SET search_path = '' AS $$
BEGIN
    IF NEW.admin_invited IS DISTINCT FROM OLD.admin_invited
       OR NEW.invited_department_id IS DISTINCT FROM OLD.invited_department_id
       OR NEW.invited_full_name IS DISTINCT FROM OLD.invited_full_name
       OR NEW.invited_profile IS DISTINCT FROM OLD.invited_profile
       OR NEW.role_name IS DISTINCT FROM OLD.role_name THEN
        RAISE EXCEPTION 'Invitation details are immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

NOTIFY pgrst, 'reload schema';
COMMIT;
