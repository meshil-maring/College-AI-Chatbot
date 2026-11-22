-- Per-administrator access areas (User Management U2, scoped administrators).
--
-- Every administrator holds the admin role's permissions. The Owner may limit
-- another administrator to some access areas; the limit is stored as the
-- allowed permission codes and the backend intersects the admin role's codes
-- with it when it loads the account. No row means full access, so existing
-- administrators keep everything until the Owner limits them. The Owner always
-- has full access: ownership moving to a limited administrator clears the row.
-- Codes not covered by any area (for example a permission added later) are
-- withheld from limited administrators. Department-limited administrators are
-- not part of this phase. Codes: P1401 not the Owner, P1402 not an
-- administrator, P1404 the Owner cannot be limited.
BEGIN;

CREATE TABLE public.institution_admin_access (
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id),
    user_id uuid NOT NULL REFERENCES public.users(id),
    areas text[] NOT NULL,
    allowed_codes text[] NOT NULL,
    updated_by uuid NOT NULL REFERENCES public.users(id),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (institution_id, user_id)
);
ALTER TABLE public.institution_admin_access ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.institution_admin_access FROM PUBLIC, anon, authenticated, service_role;
-- The backend reads the limit with the account (users -> institution_admin_access).
GRANT SELECT ON TABLE public.institution_admin_access TO service_role;

-- Access chosen when inviting an administrator; NULL means full access.
ALTER TABLE public.platform_admin_invitations ADD COLUMN invited_admin_areas text[];

-- The access areas the Owner can choose, in display order.
CREATE FUNCTION public.institution_admin_areas()
RETURNS text[] LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
    SELECT ARRAY['staff_faculty', 'students', 'academic_setup', 'content', 'staff_permissions', 'settings_audit'];
$$;

-- Permission codes for a set of areas. Every administrator keeps their own
-- profile, the assistant, institution details and read-only academic catalogue
-- (lists and labels on every page need them).
CREATE FUNCTION public.institution_admin_area_codes(p_areas text[])
RETURNS text[] LANGUAGE sql IMMUTABLE SET search_path = '' AS $$
    SELECT ARRAY(SELECT DISTINCT code FROM (
        SELECT unnest(ARRAY['profile.own.read', 'profile.own.update', 'ai.chat', 'institution.read',
            'academic_years.read', 'courses.read', 'departments.read', 'programs.read', 'sections.read',
            'section_subjects.read', 'semesters.read', 'subjects.read']) AS code
        UNION ALL
        SELECT unnest(CASE area
            WHEN 'staff_faculty' THEN ARRAY['users.create', 'users.read', 'users.update',
                'staff.approve', 'staff.create', 'staff.read', 'staff.suspend', 'staff.update',
                'faculty.approve', 'faculty.create', 'faculty.read', 'faculty.suspend', 'faculty.update',
                'roles.read', 'roles.manage']
            WHEN 'students' THEN ARRAY['students.approve', 'students.create', 'students.delete', 'students.read',
                'students.reject', 'students.suspend', 'students.update', 'transfers.approve', 'transfers.read']
            WHEN 'academic_setup' THEN ARRAY['academic_years.manage', 'courses.manage', 'departments.manage',
                'programs.manage', 'sections.manage', 'section_subjects.manage', 'semesters.manage', 'subjects.manage']
            WHEN 'content' THEN ARRAY['notices.create', 'notices.delete', 'notices.read', 'notices.update',
                'documents.create', 'documents.delete', 'documents.read', 'documents.update',
                'ai.knowledge.create', 'ai.knowledge.delete', 'ai.knowledge.read', 'ai.knowledge.update']
            WHEN 'staff_permissions' THEN ARRAY['permissions.read', 'permissions.manage']
            WHEN 'settings_audit' THEN ARRAY['institution.update', 'institution.settings.manage', 'audit.read',
                'platform.manage', 'organizations.manage']
        END)
        FROM unnest(COALESCE(p_areas, '{}'::text[])) AS area
    ) codes ORDER BY code);
$$;

-- Whether this administrator's access limit (if any) includes the code.
CREATE FUNCTION public.institution_admin_access_allows(p_user uuid, p_tenant uuid, p_code text)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = '' AS $$
    SELECT NOT EXISTS (
        SELECT 1 FROM public.institution_admin_access a
        WHERE a.institution_id = p_tenant AND a.user_id = p_user AND NOT p_code = ANY (a.allowed_codes));
$$;

-- Set another administrator's access. NULL or every area means full access.
CREATE FUNCTION public.set_institution_admin_access(p_actor uuid, p_tenant uuid, p_user uuid, p_areas text[])
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
    v_areas text[];
    v_full boolean;
BEGIN
    PERFORM public.institution_owner_assert(p_actor, p_tenant);
    IF p_user IS NULL OR NOT p_user = ANY (public.institution_admin_ids(p_tenant)) THEN
        RAISE EXCEPTION 'Choose an active administrator of the institution' USING ERRCODE = 'P1402';
    END IF;
    IF p_user = p_actor THEN
        RAISE EXCEPTION 'The Owner always has full access' USING ERRCODE = 'P1404';
    END IF;
    IF p_areas IS NOT NULL AND NOT p_areas <@ public.institution_admin_areas() THEN
        RAISE EXCEPTION 'Unknown access area' USING ERRCODE = '22023';
    END IF;
    v_full := p_areas IS NULL OR public.institution_admin_areas() <@ p_areas;
    v_areas := CASE WHEN v_full THEN NULL ELSE ARRAY(
        SELECT a FROM unnest(public.institution_admin_areas()) WITH ORDINALITY t(a, n)
        WHERE a = ANY (p_areas) ORDER BY n) END;
    PERFORM pg_advisory_xact_lock(hashtextextended('admin-access:' || p_tenant::text || ':' || p_user::text, 0));
    IF v_full THEN
        DELETE FROM public.institution_admin_access WHERE institution_id = p_tenant AND user_id = p_user;
    ELSE
        INSERT INTO public.institution_admin_access (institution_id, user_id, areas, allowed_codes, updated_by)
        VALUES (p_tenant, p_user, v_areas, public.institution_admin_area_codes(v_areas), p_actor)
        ON CONFLICT (institution_id, user_id) DO UPDATE
        SET areas = EXCLUDED.areas, allowed_codes = EXCLUDED.allowed_codes,
            updated_by = EXCLUDED.updated_by, updated_at = now();
    END IF;
    INSERT INTO public.admin_audit_log (actor_user_id, institution_id, action, table_name, record_id, record_data)
    VALUES (p_actor, p_tenant, 'institution.admin.access', 'institution_admin_access', p_user::text,
        jsonb_build_object('target_user_id', p_user, 'areas', to_jsonb(v_areas), 'full_access', v_full));
    RETURN jsonb_build_object('user_id', p_user, 'access_areas', to_jsonb(v_areas), 'full_access', v_full);
END;
$$;

-- The Owner is never limited: a new Owner's limit is cleared.
CREATE FUNCTION public.institution_owner_clear_access()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    DELETE FROM public.institution_admin_access
    WHERE institution_id = NEW.institution_id AND user_id = NEW.owner_user_id;
    RETURN NULL;
END;
$$;
CREATE TRIGGER institutions_owner_clear_access
    AFTER UPDATE OF owner_user_id ON public.institutions
    FOR EACH ROW WHEN (NEW.owner_user_id IS NOT NULL AND NEW.owner_user_id IS DISTINCT FROM OLD.owner_user_id)
    EXECUTE FUNCTION public.institution_owner_clear_access();

-- Removing the admin role ends the limit too, so a later re-invitation starts clean.
CREATE FUNCTION public.institution_admin_access_follow_grants()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    IF OLD.scope_type = 'institution' AND EXISTS (
        SELECT 1 FROM public.roles WHERE id = OLD.role_id AND name = 'admin') THEN
        DELETE FROM public.institution_admin_access WHERE institution_id = OLD.scope_id AND user_id = OLD.user_id;
    END IF;
    RETURN NULL;
END;
$$;
CREATE TRIGGER user_roles_admin_access
    AFTER DELETE ON public.user_roles
    FOR EACH ROW EXECUTE FUNCTION public.institution_admin_access_follow_grants();

-- Administrators (with their access), the Owner and pending administrator invitations.
CREATE OR REPLACE FUNCTION public.read_institution_admins(p_actor uuid, p_tenant uuid)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = '' AS $$
BEGIN
    PERFORM public.phase81_assert_institution_admin(p_actor, p_tenant);
    RETURN jsonb_build_object(
        'owner_user_id', (SELECT owner_user_id FROM public.institutions WHERE institution_id = p_tenant),
        'access_areas', to_jsonb(public.institution_admin_areas()),
        'administrators', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'user_id', u.id, 'email', u.email, 'status', u.status, 'assigned_at', ur.assigned_at,
                'name', COALESCE(NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), ''), u.email),
                'access_areas', to_jsonb(a.areas)
            ) ORDER BY ur.assigned_at, u.id)
            FROM public.user_roles ur
            JOIN public.roles r ON r.id = ur.role_id AND r.name = 'admin'
            JOIN public.users u ON u.id = ur.user_id
            LEFT JOIN public.institution_admin_access a ON a.institution_id = p_tenant AND a.user_id = u.id
            WHERE ur.scope_type = 'institution' AND ur.scope_id = p_tenant), '[]'::jsonb),
        'invitations', COALESCE((
            SELECT jsonb_agg(jsonb_build_object(
                'invitation_id', i.invitation_id, 'email', i.email, 'full_name', i.invited_full_name,
                'expires_at', i.expires_at, 'created_at', i.created_at,
                'email_delivery_status', i.email_delivery_status,
                'access_areas', to_jsonb(i.invited_admin_areas)
            ) ORDER BY i.created_at DESC)
            FROM public.platform_admin_invitations i
            WHERE i.institution_id = p_tenant AND i.role_name = 'admin' AND i.status = 'invited'
              AND i.expires_at > clock_timestamp()), '[]'::jsonb)
    );
END;
$$;


REVOKE ALL ON FUNCTION public.institution_admin_areas(), public.institution_admin_area_codes(text[]),
    public.institution_admin_access_allows(uuid, uuid, text),
    public.institution_owner_clear_access(), public.institution_admin_access_follow_grants()
    FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON FUNCTION public.set_institution_admin_access(uuid, uuid, uuid, text[])
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.set_institution_admin_access(uuid, uuid, uuid, text[]) TO service_role;

NOTIFY pgrst, 'reload schema';
COMMIT;
