-- Appointment commands with terms and the multi-department policy.
-- P1110 invalid appointment, P1114 policy allows one department per HOD,
-- P1115 invalid term dates. (P1111 already means an open student transfer.)

-- Every appointment command takes this lock first. It now also records the end
-- of appointments in this department whose planned end date has passed.
CREATE OR REPLACE FUNCTION public.department_head_lock(p_actor uuid, p_tenant uuid, p_department uuid)
RETURNS public.departments LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_department public.departments; v_expired record;
BEGIN
    PERFORM public.assert_transfer_backend();
    IF NOT public.transfer_admin_allowed(p_actor, p_tenant, 'departments.manage') THEN
        RAISE EXCEPTION 'Administrator permission required' USING ERRCODE = '42501';
    END IF;
    SELECT * INTO v_department FROM public.departments
    WHERE department_id = p_department AND institution_id = p_tenant
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Department not found' USING ERRCODE = 'P0002';
    END IF;
    FOR v_expired IN
        UPDATE public.department_heads SET ended_at = now(), ended_by = p_actor
        WHERE institution_id = p_tenant AND department_id = p_department AND ended_at IS NULL
          AND NOT public.department_head_in_effect(ended_at, planned_end_on)
        RETURNING faculty_user_id, planned_end_on
    LOOP
        INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
        VALUES (p_actor, p_tenant, 'academic.department.head.expired', 'department_heads', p_department::text,
            jsonb_build_object('faculty_user_id', v_expired.faculty_user_id,
                'planned_end_on', v_expired.planned_end_on));
    END LOOP;
    RETURN v_department;
END;
$$;

-- Every new appointment: valid term, and the institution's one-department rule.
CREATE FUNCTION public.department_head_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF NEW.starts_on > public.department_head_today() THEN
        RAISE EXCEPTION 'The start date cannot be in the future' USING ERRCODE = 'P1115';
    END IF;
    IF NEW.planned_end_on IS NOT NULL AND NEW.planned_end_on < public.department_head_today() THEN
        RAISE EXCEPTION 'The planned end date has already passed' USING ERRCODE = 'P1115';
    END IF;
    IF TG_OP = 'INSERT' AND NOT (
        SELECT allow_multi_department_hod FROM public.institutions WHERE institution_id = NEW.institution_id
    ) AND EXISTS (
        SELECT 1 FROM public.department_heads h
        WHERE h.institution_id = NEW.institution_id AND h.faculty_user_id = NEW.faculty_user_id
          AND h.department_id <> NEW.department_id
          AND public.department_head_in_effect(h.ended_at, h.planned_end_on)
    ) THEN
        RAISE EXCEPTION 'This faculty member already heads another department'
            USING ERRCODE = 'P1114';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER department_heads_guard
    BEFORE INSERT OR UPDATE OF starts_on, planned_end_on ON public.department_heads
    FOR EACH ROW EXECUTE FUNCTION public.department_head_guard();

-- Add one Head of Department with a term, without ending the others. Idempotent.
DROP FUNCTION public.add_department_head(uuid, uuid, uuid, uuid);
CREATE FUNCTION public.add_department_head(
    p_actor uuid, p_tenant uuid, p_department uuid, p_faculty uuid,
    p_starts_on date DEFAULT NULL, p_planned_end_on date DEFAULT NULL
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_department public.departments; v_before uuid[];
BEGIN
    v_department := public.department_head_lock(p_actor, p_tenant, p_department);
    IF p_faculty IS NULL OR NOT v_department.is_active
       OR NOT public.transfer_is_active_faculty(p_faculty, p_tenant) THEN
        RAISE EXCEPTION 'Choose an active faculty member for an active department'
            USING ERRCODE = 'P1110';
    END IF;
    v_before := public.department_head_ids(p_tenant, p_department);
    IF p_faculty = ANY (v_before) THEN
        RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
            'institution_id', p_tenant, 'already_applied', true, 'head_ids', to_jsonb(v_before));
    END IF;
    INSERT INTO public.department_heads
        (institution_id, department_id, faculty_user_id, assigned_by, starts_on, planned_end_on)
    VALUES (p_tenant, p_department, p_faculty, p_actor,
        COALESCE(p_starts_on, public.department_head_today()), p_planned_end_on);
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'academic.department.head.add', 'department_heads', p_department::text,
        jsonb_build_object('faculty_user_id', p_faculty, 'before', to_jsonb(v_before),
            'after', to_jsonb(public.department_head_ids(p_tenant, p_department)),
            'starts_on', COALESCE(p_starts_on, public.department_head_today()),
            'planned_end_on', p_planned_end_on));
    RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
        'institution_id', p_tenant, 'already_applied', false,
        'head_ids', to_jsonb(public.department_head_ids(p_tenant, p_department)));
END;
$$;

-- Change the term of a current appointment.
CREATE FUNCTION public.set_department_head_term(
    p_actor uuid, p_tenant uuid, p_department uuid, p_faculty uuid,
    p_starts_on date, p_planned_end_on date
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_before public.department_heads;
BEGIN
    PERFORM public.department_head_lock(p_actor, p_tenant, p_department);
    IF p_starts_on IS NULL THEN
        RAISE EXCEPTION 'The start date is required' USING ERRCODE = 'P1115';
    END IF;
    SELECT * INTO v_before FROM public.department_heads
    WHERE institution_id = p_tenant AND department_id = p_department AND faculty_user_id = p_faculty
      AND ended_at IS NULL
    FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'This faculty member is not a current head of the department' USING ERRCODE = 'P1110';
    END IF;
    UPDATE public.department_heads SET starts_on = p_starts_on, planned_end_on = p_planned_end_on
    WHERE department_head_id = v_before.department_head_id;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'academic.department.head.term', 'department_heads', p_department::text,
        jsonb_build_object('faculty_user_id', p_faculty,
            'before', jsonb_build_object('starts_on', v_before.starts_on, 'planned_end_on', v_before.planned_end_on),
            'after', jsonb_build_object('starts_on', p_starts_on, 'planned_end_on', p_planned_end_on)));
    RETURN jsonb_build_object('department_id', p_department, 'faculty_user_id', p_faculty,
        'starts_on', p_starts_on, 'planned_end_on', p_planned_end_on);
END;
$$;

-- Allow or stop one faculty member heading several departments. Existing
-- appointments are kept when the rule is switched off; only new ones are checked.
CREATE FUNCTION public.set_department_head_policy(p_actor uuid, p_tenant uuid, p_allow boolean)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_before boolean;
BEGIN
    PERFORM public.assert_transfer_backend();
    IF NOT public.transfer_admin_allowed(p_actor, p_tenant, 'departments.manage') THEN
        RAISE EXCEPTION 'Administrator permission required' USING ERRCODE = '42501';
    END IF;
    IF p_allow IS NULL THEN
        RAISE EXCEPTION 'Choose whether to allow it' USING ERRCODE = '22023';
    END IF;
    SELECT allow_multi_department_hod INTO v_before FROM public.institutions
    WHERE institution_id = p_tenant FOR UPDATE;
    IF v_before IS DISTINCT FROM p_allow THEN
        UPDATE public.institutions SET allow_multi_department_hod = p_allow WHERE institution_id = p_tenant;
        INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
        VALUES (p_actor, p_tenant, 'academic.department.head.policy', 'institutions', p_tenant::text,
            jsonb_build_object('allow_multi_department_hod', p_allow, 'before', v_before));
    END IF;
    RETURN jsonb_build_object('institution_id', p_tenant, 'allow_multi_department_hod', p_allow,
        'already_applied', v_before IS NOT DISTINCT FROM p_allow);
END;
$$;
