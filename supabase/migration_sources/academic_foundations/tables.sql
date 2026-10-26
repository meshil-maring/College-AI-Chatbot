-- Stage 1 only: degree programs, departments and institutional academic years.
-- Fail on an unexpected existing relation; historical migrations stay intact.
CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA extensions;
SET LOCAL search_path = public, extensions;

CREATE TABLE public.departments (
    department_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 160),
    code text NOT NULL CHECK (length(btrim(code)) BETWEEN 1 AND 32
        AND code ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'),
    description text CHECK (length(description) <= 2000),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (department_id, institution_id)
);
CREATE UNIQUE INDEX academic_foundation_department_code
    ON public.departments (institution_id, lower(btrim(code)));

CREATE TABLE public.programs (
    program_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    department_id uuid NOT NULL,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 160),
    code text NOT NULL CHECK (length(btrim(code)) BETWEEN 1 AND 32
        AND code ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'),
    description text CHECK (length(description) <= 2000),
    degree_type text NOT NULL CHECK (length(btrim(degree_type)) BETWEEN 1 AND 80),
    duration_years numeric NOT NULL CHECK (duration_years > 0 AND duration_years <= 20),
    total_credits numeric CHECK (total_credits > 0 AND total_credits <= 1000),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (department_id, institution_id)
        REFERENCES public.departments (department_id, institution_id) ON DELETE RESTRICT,
    UNIQUE (program_id, institution_id)
);
CREATE UNIQUE INDEX academic_foundation_program_code
    ON public.programs (institution_id, department_id, lower(btrim(code)));
CREATE INDEX academic_foundation_program_tenant ON public.programs (institution_id);

CREATE TABLE public.academic_years (
    academic_year_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    name text NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 160),
    code text NOT NULL CHECK (length(btrim(code)) BETWEEN 1 AND 32
        AND code ~ '^[A-Za-z0-9][A-Za-z0-9._/-]*$'),
    start_date date NOT NULL CHECK (isfinite(start_date)),
    end_date date NOT NULL CHECK (isfinite(end_date)),
    is_current boolean NOT NULL DEFAULT false,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (end_date > start_date),
    CHECK (NOT is_current OR is_active),
    UNIQUE (academic_year_id, institution_id),
    EXCLUDE USING gist (
        institution_id WITH =, daterange(start_date, end_date, '[]') WITH &&
    ) WHERE (is_active)
);
CREATE UNIQUE INDEX academic_foundation_year_code
    ON public.academic_years (institution_id, lower(btrim(code)));
CREATE UNIQUE INDEX academic_foundation_current_year
    ON public.academic_years (institution_id) WHERE (is_current AND is_active);

COMMENT ON TABLE public.programs IS 'Degree programs, such as B.Tech CSE; these are not reusable subjects.';
COMMENT ON TABLE public.academic_years IS 'Institutional calendar years; program study-semester contexts are a later stage.';
