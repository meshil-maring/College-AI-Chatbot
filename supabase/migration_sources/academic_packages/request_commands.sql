CREATE FUNCTION public.academic_package_request_command(
    p_actor uuid, p_tenant uuid, p_operation text, p_payload jsonb
) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE assignment public.academic_package_assignments; request public.academic_package_requests;
    class_row public.academic_classes; placement public.academic_class_placements; result jsonb; instant timestamptz;
BEGIN
    IF p_operation = 'request_change' THEN
        SELECT a.* INTO assignment FROM public.academic_package_assignments a
        JOIN public.academic_class_placements cp USING(placement_id) JOIN public.academic_classes c USING(class_id)
        WHERE a.assignment_id = (p_payload->>'assignment_id')::uuid AND c.institution_id = p_tenant FOR UPDATE OF a;
        IF NOT FOUND THEN RAISE EXCEPTION 'Assignment not found' USING ERRCODE = 'P0002'; END IF;
    ELSIF p_operation = 'review_request' THEN
        SELECT r.* INTO request FROM public.academic_package_requests r
        JOIN public.academic_package_assignments a USING(assignment_id)
        JOIN public.academic_class_placements cp USING(placement_id) JOIN public.academic_classes c USING(class_id)
        WHERE r.request_id = (p_payload->>'request_id')::uuid AND c.institution_id = p_tenant FOR UPDATE OF r;
        IF NOT FOUND THEN RAISE EXCEPTION 'Request not found' USING ERRCODE = 'P0002'; END IF;
        SELECT * INTO assignment FROM public.academic_package_assignments
        WHERE assignment_id = request.assignment_id FOR UPDATE;
    ELSE
        RAISE EXCEPTION 'Unknown request operation' USING ERRCODE = '22023';
    END IF;
    SELECT * INTO placement FROM public.academic_class_placements WHERE placement_id = assignment.placement_id;
    SELECT * INTO class_row FROM public.academic_classes WHERE class_id = placement.class_id FOR UPDATE;
    IF p_operation = 'request_change' THEN
        PERFORM public.academic_package_require(p_actor, p_tenant, 'academic.package.own.request');
        IF NOT public.academic_package_owns(p_actor, p_tenant, placement.placement_id) THEN
            RAISE EXCEPTION 'Own placement required' USING ERRCODE = '42501';
        END IF;
        IF assignment.package_id = (p_payload->>'package_id')::uuid THEN
            RAISE EXCEPTION 'Package is already assigned' USING ERRCODE = '23514';
        END IF;
        PERFORM 1 FROM public.academic_class_packages cp WHERE cp.class_id = class_row.class_id
          AND cp.package_id = (p_payload->>'package_id')::uuid AND cp.enabled FOR SHARE;
        IF NOT FOUND THEN RAISE EXCEPTION 'Requested package unavailable' USING ERRCODE = '23514'; END IF;
        instant := clock_timestamp();
        IF instant >= class_row.change_cutoff THEN
            RAISE EXCEPTION 'Package changes are closed for this class' USING ERRCODE = '23514';
        END IF;
        INSERT INTO public.academic_package_requests(assignment_id, source_revision, package_id, reason, requested_by, requested_at)
        VALUES (assignment.assignment_id, assignment.revision, (p_payload->>'package_id')::uuid,
            btrim(p_payload->>'reason'), p_actor, instant) RETURNING * INTO request;
    ELSE
        PERFORM public.academic_package_require(p_actor, p_tenant, 'academic.package.requests.review', class_row.class_id);
        IF request.status <> 'pending' THEN
            RETURN to_jsonb(request);
        END IF;
        IF clock_timestamp() >= class_row.change_cutoff THEN
            UPDATE public.academic_package_requests SET status = 'expired', reviewed_at = clock_timestamp()
            WHERE request_id = request.request_id RETURNING * INTO request;
        ELSIF request.source_revision <> assignment.revision THEN
            UPDATE public.academic_package_requests SET status = 'superseded', reviewed_at = clock_timestamp()
            WHERE request_id = request.request_id RETURNING * INTO request;
        ELSIF COALESCE((p_payload->>'approve')::boolean, false) THEN
            result := public.academic_package_apply(p_actor, p_tenant, assignment.placement_id, request.package_id,
                request.source_revision, btrim(p_payload->>'reason'), true);
            UPDATE public.academic_package_requests SET status = 'approved', reviewed_by = p_actor,
                reviewed_at = (result->>'updated_at')::timestamptz, decision_reason = btrim(p_payload->>'reason')
            WHERE request_id = request.request_id RETURNING * INTO request;
        ELSE
            UPDATE public.academic_package_requests SET status = 'rejected', reviewed_by = p_actor,
                reviewed_at = clock_timestamp(), decision_reason = btrim(p_payload->>'reason')
            WHERE request_id = request.request_id RETURNING * INTO request;
        END IF;
    END IF;
    result := to_jsonb(request);
    PERFORM public.academic_package_audit(p_actor, p_tenant, p_operation, 'academic_package_requests', request.request_id, NULL, result);
    RETURN result;
END;
$$;
