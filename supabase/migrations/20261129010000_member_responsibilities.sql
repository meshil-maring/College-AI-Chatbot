-- Class In-Charge and Subject Coordinator responsibilities (User Management U6, U7).
--
-- Like Head of Department, these are dated responsibilities of a Faculty member,
-- not roles. A Class In-Charge looks after one class section; a Subject
-- Coordinator coordinates one catalogue course across every section and term.
-- Each section and course has at most one current holder: assigning someone
-- else hands it over and keeps the earlier appointment as history.
--
-- An appointment is current while it has not ended and its planned end date has
-- not passed (department_head_in_effect, 20261129000000). Start dates cannot be
-- in the future. Ended appointments are kept; like department_heads, history
-- references keep a section or course from being deleted.
--
-- These records grant no access yet: attendance and examination modules that
-- would use them were removed on 2026-10-23. P1301 target, P1302 faculty.
BEGIN;

CREATE TABLE public.member_responsibilities (
    responsibility_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    faculty_user_id uuid NOT NULL REFERENCES public.users(id),
    responsibility text NOT NULL CHECK (responsibility IN ('class_in_charge', 'subject_coordinator')),
    academic_section_id uuid REFERENCES public.academic_sections(academic_section_id) ON DELETE RESTRICT,
    course_id uuid REFERENCES public.courses(course_id) ON DELETE RESTRICT,
    starts_on date NOT NULL,
    planned_end_on date,
    assigned_by uuid NOT NULL REFERENCES public.users(id),
    assigned_at timestamptz NOT NULL DEFAULT now(),
    ended_by uuid REFERENCES public.users(id),
    ended_at timestamptz,
    CONSTRAINT member_responsibilities_target CHECK (
        (responsibility = 'class_in_charge' AND academic_section_id IS NOT NULL AND course_id IS NULL)
        OR (responsibility = 'subject_coordinator' AND course_id IS NOT NULL AND academic_section_id IS NULL)),
    CONSTRAINT member_responsibilities_term_order CHECK (planned_end_on IS NULL OR planned_end_on >= starts_on),
    CONSTRAINT member_responsibilities_end_pair CHECK ((ended_at IS NULL) = (ended_by IS NULL))
);

CREATE UNIQUE INDEX member_responsibilities_one_class_in_charge
    ON public.member_responsibilities (academic_section_id)
    WHERE responsibility = 'class_in_charge' AND ended_at IS NULL;
CREATE UNIQUE INDEX member_responsibilities_one_coordinator
    ON public.member_responsibilities (course_id)
    WHERE responsibility = 'subject_coordinator' AND ended_at IS NULL;
CREATE INDEX member_responsibilities_faculty
    ON public.member_responsibilities (institution_id, faculty_user_id) WHERE ended_at IS NULL;

ALTER TABLE public.member_responsibilities ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.member_responsibilities FROM PUBLIC, anon, authenticated, service_role;

-- Current and past appointments of the institution, newest first, with labels.
CREATE FUNCTION public.read_member_responsibilities(p_actor uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    RETURN COALESCE((
        SELECT jsonb_agg(jsonb_build_object(
            'responsibility_id', m.responsibility_id, 'responsibility', m.responsibility,
            'faculty_user_id', m.faculty_user_id,
            'faculty_name', COALESCE(NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), ''), u.email),
            'academic_section_id', m.academic_section_id, 'course_id', m.course_id,
            'target_code', COALESCE(s.code, c.code), 'target_name', COALESCE(s.name, c.name),
            'starts_on', m.starts_on, 'planned_end_on', m.planned_end_on, 'ended_at', m.ended_at,
            'is_current', public.department_head_in_effect(m.ended_at, m.planned_end_on)
        ) ORDER BY public.department_head_in_effect(m.ended_at, m.planned_end_on) DESC, m.assigned_at DESC)
        FROM public.member_responsibilities m
        JOIN public.users u ON u.id = m.faculty_user_id
        LEFT JOIN public.academic_sections s ON s.academic_section_id = m.academic_section_id
        LEFT JOIN public.courses c ON c.course_id = m.course_id
        WHERE m.institution_id = p_tenant
    ), '[]'::jsonb);
END;
$$;

-- Appoint a Faculty member; hands over from the current holder if there is one.
CREATE FUNCTION public.assign_member_responsibility(
    p_actor uuid, p_tenant uuid, p_faculty uuid, p_responsibility text, p_target uuid,
    p_starts_on date DEFAULT NULL, p_planned_end_on date DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_today date := public.department_head_today();
    v_starts date := COALESCE(p_starts_on, public.department_head_today());
    v_current public.member_responsibilities;
    v_section boolean := p_responsibility = 'class_in_charge';
    v_row public.member_responsibilities;
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    IF p_responsibility IS NULL OR p_responsibility NOT IN ('class_in_charge', 'subject_coordinator') THEN
        RAISE EXCEPTION 'Unsupported responsibility' USING ERRCODE = '22023';
    END IF;
    IF v_starts > v_today OR (p_planned_end_on IS NOT NULL AND
        (p_planned_end_on < v_today OR p_planned_end_on < v_starts)) THEN
        RAISE EXCEPTION 'Check the start and planned end dates' USING ERRCODE = '22023';
    END IF;
    IF v_section THEN
        PERFORM 1 FROM public.academic_sections
        WHERE academic_section_id = p_target AND institution_id = p_tenant AND is_active FOR UPDATE;
    ELSE
        PERFORM 1 FROM public.courses c JOIN public.departments d ON d.department_id = c.department_id
        WHERE c.course_id = p_target AND d.institution_id = p_tenant AND c.is_active FOR UPDATE OF c;
    END IF;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Choose an active class section or course of this institution' USING ERRCODE = 'P1301';
    END IF;
    IF p_faculty IS NULL OR NOT public.transfer_is_active_faculty(p_faculty, p_tenant) THEN
        RAISE EXCEPTION 'Choose an active faculty member' USING ERRCODE = 'P1302';
    END IF;
    -- Record the end of an appointment whose planned end date has passed.
    UPDATE public.member_responsibilities SET ended_at = now(), ended_by = p_actor
    WHERE responsibility = p_responsibility AND ended_at IS NULL
      AND (academic_section_id = p_target OR course_id = p_target)
      AND NOT public.department_head_in_effect(ended_at, planned_end_on);
    SELECT * INTO v_current FROM public.member_responsibilities
    WHERE responsibility = p_responsibility AND ended_at IS NULL
      AND (academic_section_id = p_target OR course_id = p_target);
    IF FOUND AND v_current.faculty_user_id = p_faculty THEN
        RETURN to_jsonb(v_current) || jsonb_build_object('already_applied', true);
    END IF;
    IF FOUND THEN
        UPDATE public.member_responsibilities SET ended_at = now(), ended_by = p_actor
        WHERE responsibility_id = v_current.responsibility_id;
    END IF;
    INSERT INTO public.member_responsibilities (institution_id, faculty_user_id, responsibility,
        academic_section_id, course_id, starts_on, planned_end_on, assigned_by)
    VALUES (p_tenant, p_faculty, p_responsibility,
        CASE WHEN v_section THEN p_target END, CASE WHEN v_section THEN NULL ELSE p_target END,
        v_starts, p_planned_end_on, p_actor)
    RETURNING * INTO v_row;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'member.responsibility.assign', 'member_responsibilities',
        v_row.responsibility_id::text, jsonb_build_object('responsibility', p_responsibility,
            'target_id', p_target, 'faculty_user_id', p_faculty, 'starts_on', v_starts,
            'planned_end_on', p_planned_end_on, 'replaced_faculty_user_id', v_current.faculty_user_id));
    RETURN to_jsonb(v_row) || jsonb_build_object('already_applied', false);
END;
$$;

-- End an appointment now. Idempotent; the record is kept as history.
CREATE FUNCTION public.end_member_responsibility(p_actor uuid, p_tenant uuid, p_responsibility_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_row public.member_responsibilities;
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    SELECT * INTO v_row FROM public.member_responsibilities
    WHERE responsibility_id = p_responsibility_id AND institution_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Responsibility not found' USING ERRCODE = 'P0002';
    END IF;
    IF v_row.ended_at IS NOT NULL THEN
        RETURN to_jsonb(v_row) || jsonb_build_object('already_applied', true);
    END IF;
    UPDATE public.member_responsibilities SET ended_at = now(), ended_by = p_actor
    WHERE responsibility_id = p_responsibility_id RETURNING * INTO v_row;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'member.responsibility.end', 'member_responsibilities',
        p_responsibility_id::text, jsonb_build_object('responsibility', v_row.responsibility,
            'faculty_user_id', v_row.faculty_user_id));
    RETURN to_jsonb(v_row) || jsonb_build_object('already_applied', false);
END;
$$;

REVOKE ALL ON FUNCTION public.read_member_responsibilities(uuid, uuid),
    public.assign_member_responsibility(uuid, uuid, uuid, text, uuid, date, date),
    public.end_member_responsibility(uuid, uuid, uuid)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.read_member_responsibilities(uuid, uuid),
    public.assign_member_responsibility(uuid, uuid, uuid, text, uuid, date, date),
    public.end_member_responsibility(uuid, uuid, uuid)
    TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
