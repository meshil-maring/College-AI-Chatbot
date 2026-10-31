-- Minimal account/tenancy scaffolding for the in-memory PostgreSQL verifier.
-- Academic tables, writers, guards and authorization come from real SQL sources.
CREATE ROLE anon;
CREATE ROLE authenticated;
CREATE ROLE service_role;
CREATE SCHEMA auth;
CREATE SCHEMA extensions;
CREATE FUNCTION auth.role() RETURNS text LANGUAGE sql STABLE AS $$
    SELECT current_setting('request.jwt.claim.role', true)
$$;
CREATE TABLE auth.users (id uuid PRIMARY KEY, email text);
CREATE TABLE public.organizations (
    organization_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_code text UNIQUE, status text DEFAULT 'active'
);
CREATE TABLE public.institutions (
    institution_id uuid PRIMARY KEY, organization_id uuid REFERENCES public.organizations,
    name text, code text UNIQUE, status text DEFAULT 'active', is_active boolean DEFAULT true
);
CREATE TABLE public.campuses (
    campus_id uuid PRIMARY KEY, institution_id uuid REFERENCES public.institutions,
    UNIQUE(institution_id, campus_id)
);
CREATE TABLE public.users (
    id uuid PRIMARY KEY, auth_user_id uuid REFERENCES auth.users,
    email text, first_name text, last_name text, status text DEFAULT 'active'
);
CREATE TABLE public.students (
    student_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), user_id uuid REFERENCES public.users,
    institution_id uuid REFERENCES public.institutions, approval_status text DEFAULT 'approved',
    status text DEFAULT 'active', is_active boolean DEFAULT true
);
CREATE TABLE public.roles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text UNIQUE, is_active boolean DEFAULT true
);
CREATE TABLE public.permissions (
    permission_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), code text UNIQUE,
    name text, description text, scope text, is_active boolean DEFAULT true,
    updated_at timestamptz DEFAULT now()
);
CREATE TABLE public.role_permissions (
    role_id uuid REFERENCES public.roles, permission_id uuid REFERENCES public.permissions,
    PRIMARY KEY(role_id, permission_id)
);
CREATE TABLE public.user_roles (
    user_id uuid REFERENCES public.users, role_id uuid REFERENCES public.roles,
    scope_type text, scope_id uuid, scope_organization_id uuid REFERENCES public.organizations
);
CREATE TABLE public.admin_audit_log (
    audit_id uuid PRIMARY KEY DEFAULT gen_random_uuid(), actor_user_id uuid REFERENCES public.users,
    institution_id uuid REFERENCES public.institutions, action text, table_name text,
    record_id text, record_data jsonb, created_at timestamptz DEFAULT now()
);
INSERT INTO public.organizations(organization_code) VALUES('COLLEGE-AI-PLATFORM');
INSERT INTO public.roles(name) VALUES('admin'), ('staff'), ('student');
