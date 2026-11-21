import type {
  CurrentPlacement,
  StudentTransfers,
  TransferOption,
  TransferRequest,
  TransferReviews,
  TransferSection,
} from '../../../types/transfer.ts'

export function sectionFixture(overrides: Partial<TransferSection> = {}): TransferSection {
  return {
    academic_section_id: 'section-a',
    section_name: 'A',
    section_code: 'CSE-3A',
    admission_cohort_id: 'cohort-cse-2024',
    batch_name: '2024 batch',
    program_id: 'program-cse',
    program_name: 'B.Tech CSE',
    program_code: 'CSE',
    department_id: 'department-cs',
    department_name: 'Computer Science',
    program_semester_name: 'Semester 3',
    semester_id: 'term-1',
    term_name: 'Odd term 2026',
    capacity: 60,
    seats_taken: 40,
    ...overrides,
  }
}

export function currentFixture(overrides: Partial<CurrentPlacement> = {}): CurrentPlacement {
  return {
    ...sectionFixture(),
    semester_registration_id: 'registration-1',
    registration_status: 'registered',
    term_end_date: '2026-12-20',
    term_open: true,
    ...overrides,
  }
}

export function optionFixture(overrides: Partial<TransferOption> = {}): TransferOption {
  return {
    ...sectionFixture({ academic_section_id: 'section-b', section_name: 'B', section_code: 'CSE-3B' }),
    transfer_type: 'section_transfer',
    has_seat: true,
    ...overrides,
  }
}

export function requestFixture(overrides: Partial<TransferRequest> = {}): TransferRequest {
  return {
    transfer_request_id: 'request-1',
    student_id: 'student-1',
    student_name: 'Asha Rao',
    register_number: 'REG-001',
    transfer_type: 'section_transfer',
    status: 'submitted',
    reason: 'My section timetable clashes with my lab work.',
    from_section: sectionFixture(),
    to_section: sectionFixture({ academic_section_id: 'section-b', section_name: 'B' }),
    submitted_at: '2026-11-20T10:00:00Z',
    review_started_at: null,
    decided_at: null,
    decided_as: null,
    decision_comment: null,
    cancelled_at: null,
    previous_enrollments: [],
    events: [{ action: 'submitted', comment: null, created_at: '2026-11-20T10:00:00Z' }],
    ...overrides,
  }
}

export function studentTransfersFixture(overrides: Partial<StudentTransfers> = {}): StudentTransfers {
  return {
    institution_id: 'tenant-1',
    current: currentFixture(),
    options: [
      optionFixture(),
      optionFixture({
        academic_section_id: 'section-ece',
        section_name: 'E1',
        program_id: 'program-ece',
        program_name: 'B.Tech ECE',
        department_name: 'Electronics',
        transfer_type: 'program_transfer',
        has_seat: false,
        capacity: 30,
        seats_taken: 30,
      }),
    ],
    requests: [],
    ...overrides,
  }
}

export function reviewsFixture(overrides: Partial<TransferReviews> = {}): TransferReviews {
  return {
    institution_id: 'tenant-1',
    can_review: true,
    can_decide: true,
    reviewer_role: 'hod',
    departments: [{ department_id: 'department-cs', name: 'Computer Science' }],
    requests: [requestFixture()],
    ...overrides,
  }
}
