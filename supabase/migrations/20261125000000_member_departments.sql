-- Staff and Faculty departments chosen by the institution administrator.
--
-- Applicants no longer choose their own department. The administrator picks it
-- when approving the membership request and can change it later from the
-- Staff and Faculty Management roster. One department per member per
-- institution. Only the backend service role reads or writes this table; the
-- API checks the administrator's grant, the member's active Staff/Faculty
-- grant and the department's institution before every write.

CREATE TABLE public.institution_member_departments (
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE CASCADE,
    user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    -- RESTRICT keeps a department in use from being deleted; the unused-department
    -- deletion check discovers this reference through its foreign-key scan.
    department_id uuid NOT NULL REFERENCES public.departments(department_id) ON DELETE RESTRICT,
    assigned_by uuid REFERENCES public.users(id) ON DELETE SET NULL,
    assigned_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (institution_id, user_id)
);

CREATE INDEX institution_member_departments_department
    ON public.institution_member_departments (department_id);

-- Deployed departments expose only their primary key, so tenant ownership is
-- enforced here: a member's department must belong to the same institution.
CREATE FUNCTION public.institution_member_departments_same_tenant()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.departments d
        WHERE d.department_id = NEW.department_id
          AND d.institution_id = NEW.institution_id
    ) THEN
        RAISE EXCEPTION 'Department does not belong to this institution'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER institution_member_departments_same_tenant
    BEFORE INSERT OR UPDATE ON public.institution_member_departments
    FOR EACH ROW EXECUTE FUNCTION public.institution_member_departments_same_tenant();

REVOKE ALL ON FUNCTION public.institution_member_departments_same_tenant() FROM PUBLIC, anon, authenticated;

ALTER TABLE public.institution_member_departments ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.institution_member_departments FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON TABLE public.institution_member_departments TO service_role;
