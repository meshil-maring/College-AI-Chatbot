-- One placement move shared by request approval and direct transfers. The
-- caller holds the tenant academic lock and has authorized p_role.
CREATE FUNCTION public.transfer_apply(
    p_actor uuid, p_tenant uuid, p_request uuid, p_role text, p_comment text
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_request public.student_transfer_requests; v_registration public.student_semester_registrations;
    v_enrollments jsonb;
BEGIN
    SELECT * INTO v_request FROM public.student_transfer_requests
    WHERE transfer_request_id = p_request AND institution_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transfer request not found' USING ERRCODE = 'P0002';
    END IF;
    SELECT * INTO v_registration FROM public.student_semester_registrations
    WHERE semester_registration_id = v_request.semester_registration_id AND institution_id = p_tenant
    FOR UPDATE;
    IF NOT FOUND OR v_registration.student_id <> v_request.student_id
       OR v_registration.academic_section_id <> v_request.from_section_id
       OR v_registration.semester_registration_id IS DISTINCT FROM
          public.transfer_current_registration(v_request.student_id, p_tenant) THEN
        RAISE EXCEPTION 'The student''s section changed after this request was submitted'
            USING ERRCODE = 'P1102';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.semesters WHERE semester_id = v_registration.semester_id
                   AND is_active AND end_date >= current_date) THEN
        RAISE EXCEPTION 'The current term is closed' USING ERRCODE = 'P1103';
    END IF;
    IF public.transfer_target_type(v_request.from_section_id, v_request.to_section_id, p_tenant)
       IS DISTINCT FROM v_request.transfer_type THEN
        RAISE EXCEPTION 'The requested section is unavailable' USING ERRCODE = 'P1104';
    END IF;
    IF NOT public.transfer_section_has_seat(v_request.to_section_id) THEN
        RAISE EXCEPTION 'The requested section is full' USING ERRCODE = 'P1105';
    END IF;
    SELECT COALESCE(jsonb_agg(soe.subject_snapshot || jsonb_build_object(
            'academic_offering_id', soe.academic_offering_id, 'enrolled_at', soe.enrolled_at)
        ORDER BY soe.enrolled_at, soe.offering_enrollment_id), '[]'::jsonb)
    INTO v_enrollments
    FROM public.student_offering_enrollments soe
    WHERE soe.semester_registration_id = v_registration.semester_registration_id;
    -- Offerings belong to the old section, so they cannot follow the student.
    DELETE FROM public.student_offering_enrollments
    WHERE semester_registration_id = v_registration.semester_registration_id;
    UPDATE public.student_semester_registrations
    SET academic_section_id = v_request.to_section_id, status = 'assigned',
        selected_option_ids = '{}'::uuid[], registered_at = NULL, assigned_at = now()
    WHERE semester_registration_id = v_registration.semester_registration_id;
    UPDATE public.student_transfer_requests
    SET status = 'approved', decided_by = p_actor, decided_at = now(), decided_as = p_role,
        decision_comment = p_comment, previous_registration = to_jsonb(v_registration),
        previous_enrollments = v_enrollments, updated_at = now()
    WHERE transfer_request_id = p_request;
END;
$$;

-- Same contract as before; approval now delegates the move to transfer_apply.
CREATE OR REPLACE FUNCTION public.decide_student_transfer(
    p_actor uuid, p_tenant uuid, p_request uuid, p_action text, p_comment text
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE v_request public.student_transfer_requests; v_role text; v_status text;
    v_comment text := NULLIF(btrim(COALESCE(p_comment, '')), '');
BEGIN
    PERFORM public.assert_transfer_backend();
    IF p_action IS NULL OR p_action NOT IN ('start_review', 'approve', 'reject') THEN
        RAISE EXCEPTION 'Unknown transfer action' USING ERRCODE = '22023';
    END IF;
    IF length(v_comment) > 2000 THEN
        RAISE EXCEPTION 'Comments are limited to 2000 characters' USING ERRCODE = '22023';
    END IF;
    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended('academic-setup:' || p_tenant::text, 0));
    SELECT * INTO v_request FROM public.student_transfer_requests
    WHERE transfer_request_id = p_request AND institution_id = p_tenant FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transfer request not found' USING ERRCODE = 'P0002';
    END IF;
    IF public.transfer_admin_allowed(p_actor, p_tenant, 'transfers.approve') THEN
        v_role := 'admin';
    ELSIF v_request.to_department_id = ANY (public.transfer_hod_departments(p_actor, p_tenant)) THEN
        v_role := 'hod';
    ELSE
        RAISE EXCEPTION 'Only an administrator or the receiving department HOD can decide this request'
            USING ERRCODE = '42501';
    END IF;
    IF v_request.status NOT IN ('submitted', 'under_review') THEN
        RAISE EXCEPTION 'This transfer request is already closed' USING ERRCODE = 'P1101';
    END IF;
    IF p_action = 'start_review' THEN
        IF v_request.status = 'submitted' THEN
            UPDATE public.student_transfer_requests
            SET status = 'under_review', review_started_by = p_actor,
                review_started_at = now(), updated_at = now()
            WHERE transfer_request_id = p_request;
            INSERT INTO public.student_transfer_events
                (institution_id, transfer_request_id, actor_user_id, action, comment)
            VALUES (p_tenant, p_request, p_actor, 'review_started', v_comment);
        END IF;
        v_status := 'under_review';
    ELSIF p_action = 'reject' THEN
        IF v_comment IS NULL THEN
            RAISE EXCEPTION 'A rejection reason is required' USING ERRCODE = 'P1109';
        END IF;
        UPDATE public.student_transfer_requests
        SET status = 'rejected', decided_by = p_actor, decided_at = now(), decided_as = v_role,
            decision_comment = v_comment, updated_at = now()
        WHERE transfer_request_id = p_request;
        INSERT INTO public.student_transfer_events
            (institution_id, transfer_request_id, actor_user_id, action, comment)
        VALUES (p_tenant, p_request, p_actor, 'rejected', v_comment);
        v_status := 'rejected';
    ELSE
        PERFORM public.transfer_apply(p_actor, p_tenant, p_request, v_role, v_comment);
        INSERT INTO public.student_transfer_events
            (institution_id, transfer_request_id, actor_user_id, action, comment)
        VALUES (p_tenant, p_request, p_actor, 'approved', v_comment);
        v_status := 'approved';
    END IF;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'academic.transfer.' || p_action, 'student_transfer_requests',
        p_request::text, jsonb_build_object('decided_as', v_role, 'before_status', v_request.status,
            'after_status', v_status, 'comment', v_comment));
    RETURN jsonb_build_object('transfer_request_id', p_request, 'institution_id', p_tenant,
        'status', v_status);
END;
$$;
