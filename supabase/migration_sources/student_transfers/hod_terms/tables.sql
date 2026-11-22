-- Head of Department terms (User Management U7).
--
-- HOD is a dated responsibility of a Faculty member, not a role. An appointment
-- has a start date and an optional planned end date. It counts as current while
-- it is not ended and its planned end date has not passed, so an appointment
-- that runs out stops granting HOD authority on the following day without any
-- scheduled job. The commands record the end of such appointments the next time
-- the department's heads change. Start dates cannot be in the future, so a
-- current appointment never waits to begin.
ALTER TABLE public.department_heads
    ADD COLUMN starts_on date,
    ADD COLUMN planned_end_on date;
UPDATE public.department_heads SET starts_on = (assigned_at AT TIME ZONE 'UTC')::date;
ALTER TABLE public.department_heads
    ALTER COLUMN starts_on SET NOT NULL,
    ALTER COLUMN starts_on SET DEFAULT (now() AT TIME ZONE 'UTC')::date,
    ADD CONSTRAINT department_heads_term_order
        CHECK (planned_end_on IS NULL OR planned_end_on >= starts_on);

-- Whether one faculty member may head several departments at once. Allowed by
-- default, which keeps the behavior every institution had before this setting.
ALTER TABLE public.institutions
    ADD COLUMN allow_multi_department_hod boolean NOT NULL DEFAULT true;

-- The calendar date used for terms. Dates are compared in UTC.
CREATE FUNCTION public.department_head_today()
RETURNS date LANGUAGE sql STABLE SET search_path = '' AS $$
    SELECT (now() AT TIME ZONE 'UTC')::date;
$$;

-- True while the appointment grants HOD authority.
CREATE FUNCTION public.department_head_in_effect(p_ended_at timestamptz, p_planned_end_on date)
RETURNS boolean LANGUAGE sql STABLE SET search_path = '' AS $$
    SELECT p_ended_at IS NULL
       AND (p_planned_end_on IS NULL OR p_planned_end_on >= public.department_head_today());
$$;
