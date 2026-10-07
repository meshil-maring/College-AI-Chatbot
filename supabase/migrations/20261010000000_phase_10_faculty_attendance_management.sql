-- Phase 10: Faculty attendance management.
-- Reuses the existing academic hierarchy, students identity model, RBAC, and
-- admin_audit_log. Imported rows are staged and reviewed before promotion.

CREATE TABLE IF NOT EXISTS public.faculty_attendance_rosters (
    roster_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    section_id uuid NOT NULL REFERENCES public.sections(section_id) ON DELETE RESTRICT,
    course_offering_id uuid NOT NULL REFERENCES public.course_offerings(course_offering_id) ON DELETE RESTRICT,
    semester_id uuid NOT NULL REFERENCES public.semesters(semester_id) ON DELETE RESTRICT,
    register_number text NOT NULL,
    university_roll_number text,
    student_name text NOT NULL,
    email text,
    address text,
    roster_status text NOT NULL DEFAULT 'UNREGISTERED'
        CHECK (roster_status IN ('UNREGISTERED','PENDING_APPROVAL','ACTIVE','INACTIVE')),
    linked_student_id uuid REFERENCES public.students(student_id) ON DELETE SET NULL,
    source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    imported_summary jsonb,
    created_by uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT faculty_attendance_roster_register_nonblank CHECK (btrim(register_number) <> ''),
    CONSTRAINT faculty_attendance_roster_name_nonblank CHECK (btrim(student_name) <> ''),
    UNIQUE (institution_id, section_id, register_number),
    UNIQUE (institution_id, section_id, university_roll_number)
);

CREATE TABLE IF NOT EXISTS public.faculty_attendance_sessions (
    session_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    section_id uuid NOT NULL REFERENCES public.sections(section_id) ON DELETE RESTRICT,
    course_offering_id uuid NOT NULL REFERENCES public.course_offerings(course_offering_id) ON DELETE RESTRICT,
    session_date date NOT NULL,
    conducted_by uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    source_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (section_id, session_date)
);

CREATE TABLE IF NOT EXISTS public.faculty_attendance_records (
    record_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid NOT NULL REFERENCES public.faculty_attendance_sessions(session_id) ON DELETE CASCADE,
    roster_id uuid NOT NULL REFERENCES public.faculty_attendance_rosters(roster_id) ON DELETE CASCADE,
    status text NOT NULL CHECK (status IN ('present','absent','late','excused')),
    notes text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (session_id, roster_id)
);

CREATE TABLE IF NOT EXISTS public.faculty_attendance_imports (
    import_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id uuid NOT NULL REFERENCES public.institutions(institution_id) ON DELETE RESTRICT,
    section_id uuid NOT NULL REFERENCES public.sections(section_id) ON DELETE RESTRICT,
    course_offering_id uuid NOT NULL REFERENCES public.course_offerings(course_offering_id) ON DELETE RESTRICT,
    academic_year_id uuid NOT NULL REFERENCES public.academic_years(academic_year_id) ON DELETE RESTRICT,
    semester_id uuid NOT NULL REFERENCES public.semesters(semester_id) ON DELETE RESTRICT,
    uploaded_by uuid NOT NULL REFERENCES public.users(id) ON DELETE RESTRICT,
    original_filename text NOT NULL,
    file_type text NOT NULL,
    processing_strategy text NOT NULL CHECK (processing_strategy IN ('CSV','XLS','XLSX','PDF_TEXT','OCR_AI')),
    ai_confirmation_required boolean NOT NULL DEFAULT false,
    ai_confirmed_at timestamptz,
    status text NOT NULL DEFAULT 'UPLOADED'
        CHECK (status IN ('PROCESSING','UPLOADED','VALIDATED','REVIEWED','IMPORTED','PARTIALLY_IMPORTED','FAILED')),
    summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.faculty_attendance_import_rows (
    import_row_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    import_id uuid NOT NULL REFERENCES public.faculty_attendance_imports(import_id) ON DELETE CASCADE,
    row_number integer NOT NULL,
    raw_data jsonb NOT NULL,
    normalized_data jsonb,
    validation_status text NOT NULL DEFAULT 'ERROR' CHECK (validation_status IN ('VALID','ERROR','DUPLICATE','CONFLICT','UPDATE','NEW')),
    errors jsonb NOT NULL DEFAULT '[]'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (import_id, row_number)
);

CREATE INDEX IF NOT EXISTS idx_faculty_attendance_rosters_section ON public.faculty_attendance_rosters(section_id, roster_status);
CREATE INDEX IF NOT EXISTS idx_faculty_attendance_rosters_identity ON public.faculty_attendance_rosters(institution_id, register_number, university_roll_number);
CREATE INDEX IF NOT EXISTS idx_faculty_attendance_sessions_section_date ON public.faculty_attendance_sessions(section_id, session_date DESC);
CREATE INDEX IF NOT EXISTS idx_faculty_attendance_imports_section ON public.faculty_attendance_imports(section_id, created_at DESC);

-- Keep the project-wide updated_at convention for mutable rows.
CREATE OR REPLACE FUNCTION public.faculty_attendance_set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_faculty_attendance_rosters_updated_at ON public.faculty_attendance_rosters;
CREATE TRIGGER trg_faculty_attendance_rosters_updated_at
BEFORE UPDATE ON public.faculty_attendance_rosters
FOR EACH ROW EXECUTE FUNCTION public.faculty_attendance_set_updated_at();

DROP TRIGGER IF EXISTS trg_faculty_attendance_records_updated_at ON public.faculty_attendance_records;
CREATE TRIGGER trg_faculty_attendance_records_updated_at
BEFORE UPDATE ON public.faculty_attendance_records
FOR EACH ROW EXECUTE FUNCTION public.faculty_attendance_set_updated_at();

DROP TRIGGER IF EXISTS trg_faculty_attendance_imports_updated_at ON public.faculty_attendance_imports;
CREATE TRIGGER trg_faculty_attendance_imports_updated_at
BEFORE UPDATE ON public.faculty_attendance_imports
FOR EACH ROW EXECUTE FUNCTION public.faculty_attendance_set_updated_at();

-- The REST client uses service_role, but database invariants must still hold
-- if a caller supplies forged section, offering, semester, or tenant values.
CREATE OR REPLACE FUNCTION public.faculty_attendance_context_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    section_institution uuid;
    section_offering uuid;
    section_semester uuid;
    section_year uuid;
BEGIN
    SELECT d.institution_id, sec.course_offering_id, co.semester_id, co.academic_year_id
      INTO section_institution, section_offering, section_semester, section_year
      FROM sections sec
      JOIN course_offerings co ON co.course_offering_id = sec.course_offering_id
      JOIN courses c ON c.course_id = co.course_id
      JOIN departments d ON d.department_id = c.department_id
     WHERE sec.section_id = NEW.section_id;
    IF section_institution IS NULL THEN
        RAISE EXCEPTION 'attendance section does not exist';
    END IF;
    IF NEW.institution_id IS DISTINCT FROM section_institution
       OR NEW.course_offering_id IS DISTINCT FROM section_offering THEN
        RAISE EXCEPTION 'attendance tenant or course offering does not match section';
    END IF;
    IF TG_TABLE_NAME = 'faculty_attendance_rosters'
       AND NEW.linked_student_id IS NOT NULL
       AND NOT EXISTS (
           SELECT 1 FROM students
            WHERE student_id = NEW.linked_student_id
              AND institution_id = section_institution
       ) THEN
        RAISE EXCEPTION 'linked attendance student does not belong to the section institution';
    END IF;
    IF TG_TABLE_NAME = 'faculty_attendance_rosters'
       AND NEW.semester_id IS DISTINCT FROM section_semester THEN
        RAISE EXCEPTION 'attendance roster semester does not match section';
    END IF;
    IF TG_TABLE_NAME = 'faculty_attendance_imports'
       AND (NEW.semester_id IS DISTINCT FROM section_semester
            OR NEW.academic_year_id IS DISTINCT FROM section_year) THEN
        RAISE EXCEPTION 'attendance import academic context does not match section';
    END IF;
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_faculty_attendance_roster_context ON public.faculty_attendance_rosters;
CREATE TRIGGER trg_faculty_attendance_roster_context
BEFORE INSERT OR UPDATE ON public.faculty_attendance_rosters
FOR EACH ROW EXECUTE FUNCTION public.faculty_attendance_context_guard();

DROP TRIGGER IF EXISTS trg_faculty_attendance_import_context ON public.faculty_attendance_imports;
CREATE TRIGGER trg_faculty_attendance_import_context
BEFORE INSERT OR UPDATE ON public.faculty_attendance_imports
FOR EACH ROW EXECUTE FUNCTION public.faculty_attendance_context_guard();

DROP TRIGGER IF EXISTS trg_faculty_attendance_session_context ON public.faculty_attendance_sessions;
CREATE TRIGGER trg_faculty_attendance_session_context
BEFORE INSERT OR UPDATE ON public.faculty_attendance_sessions
FOR EACH ROW EXECUTE FUNCTION public.faculty_attendance_context_guard();

CREATE OR REPLACE FUNCTION public.faculty_attendance_record_scope_guard()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    session_section uuid;
    roster_section uuid;
BEGIN
    SELECT section_id INTO session_section FROM faculty_attendance_sessions WHERE session_id = NEW.session_id;
    SELECT section_id INTO roster_section FROM faculty_attendance_rosters WHERE roster_id = NEW.roster_id;
    IF session_section IS NULL OR roster_section IS NULL OR session_section IS DISTINCT FROM roster_section THEN
        RAISE EXCEPTION 'attendance record session and roster must belong to the same section';
    END IF;
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_faculty_attendance_record_scope ON public.faculty_attendance_records;
CREATE TRIGGER trg_faculty_attendance_record_scope
BEFORE INSERT OR UPDATE ON public.faculty_attendance_records
FOR EACH ROW EXECUTE FUNCTION public.faculty_attendance_record_scope_guard();

ALTER TABLE public.faculty_attendance_rosters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.faculty_attendance_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.faculty_attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.faculty_attendance_imports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.faculty_attendance_import_rows ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.faculty_attendance_rosters, public.faculty_attendance_sessions,
    public.faculty_attendance_records, public.faculty_attendance_imports,
    public.faculty_attendance_import_rows FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO service_role;

COMMENT ON TABLE public.faculty_attendance_import_rows IS 'Untrusted staging rows; never authoritative until explicit review/import.';
COMMENT ON COLUMN public.faculty_attendance_rosters.imported_summary IS 'Imported percentage/count summary with provenance; never treated as session records.';

CREATE OR REPLACE FUNCTION public.reconcile_faculty_attendance_roster_student()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
    candidate uuid;
    by_roll uuid;
BEGIN
    IF NEW.register_number IS NULL AND NEW.university_roll_number IS NULL THEN RETURN NEW; END IF;
    -- Registration creates an identity candidate; reconciliation is only
    -- authoritative after the existing approval workflow approves it.
    IF NEW.approval_status IS DISTINCT FROM 'approved' THEN RETURN NEW; END IF;
    SELECT s.student_id INTO candidate FROM public.students s
      WHERE s.institution_id = NEW.institution_id
        AND s.register_number = NEW.register_number
      LIMIT 1;
    SELECT s.student_id INTO by_roll FROM public.students s
      WHERE s.institution_id = NEW.institution_id AND NEW.university_roll_number IS NOT NULL
        AND s.university_roll_number = NEW.university_roll_number LIMIT 1;
    IF candidate IS NULL THEN candidate := by_roll; END IF;
    IF candidate IS NOT NULL AND (by_roll IS NULL OR by_roll = candidate) THEN
        UPDATE public.faculty_attendance_rosters r
           SET linked_student_id = candidate,
               roster_status = 'ACTIVE',
               updated_at = now()
         WHERE r.institution_id = NEW.institution_id
           AND r.linked_student_id IS NULL
           AND (r.register_number = NEW.register_number OR (NEW.university_roll_number IS NOT NULL AND r.university_roll_number = NEW.university_roll_number));
    END IF;
    RETURN NEW;
END; $$;

DROP TRIGGER IF EXISTS trg_reconcile_faculty_attendance_roster ON public.students;
CREATE TRIGGER trg_reconcile_faculty_attendance_roster
AFTER INSERT OR UPDATE OF register_number, university_roll_number, approval_status ON public.students
FOR EACH ROW EXECUTE FUNCTION public.reconcile_faculty_attendance_roster_student();
