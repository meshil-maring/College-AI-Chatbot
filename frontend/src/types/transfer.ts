/**
 * Student Academic Transfer System — TypeScript contracts.
 *
 * Mirrors the backend contracts defined in
 * backend/app/schemas/students/transfer_request.py.
 *
 * The backend is authoritative; only fields actually returned are declared.
 */

export type TransferType = 'program_transfer' | 'section_transfer' | 'semester_placement';
export type TransferStatus =
  | 'submitted'
  | 'under_review'
  | 'eligible'
  | 'not_eligible'
  | 'approved'
  | 'rejected'
  | 'completed'
  | 'cancelled';
export type EligibilityStatus = 'eligible' | 'not_eligible' | 'manual_review' | 'pending';
export type TransferAction = 'submitted' | 'reviewed' | 'approved' | 'rejected' | 'completed' | 'cancelled';

export interface TransferDocument {
  file_name: string;
  file_url: string | null;
  file_type: string | null;
  size_bytes: number | null;
  uploaded_at: string | null;
}

export interface AcademicPlacement {
  program_id: string | null;
  program_name: string | null;
  program_code: string | null;
  batch_id: string | null;
  batch_name: string | null;
  batch_code: string | null;
  section_id: string | null;
  section_name: string | null;
  section_code: string | null;
  semester_id: string | null;
  semester_name: string | null;
  curriculum_version_id: string | null;
  curriculum_version: string | null;
  effective_from: string | null;
  effective_to: string | null;
  is_active: boolean | null;
}

export interface TransferActionRecord {
  action_id: string;
  action: TransferAction;
  actor_user_id: string;
  comments: string | null;
  from_status: string | null;
  to_status: string | null;
  created_at: string;
}

export interface TransferRequestView {
  request_id: string;
  student_id: string;
  institution_id: string;
  transfer_type: TransferType;
  status: TransferStatus;
  eligibility_status: EligibilityStatus | null;
  current_placement: AcademicPlacement;
  target_placement: AcademicPlacement;
  reason: string;
  supporting_documents: TransferDocument[];
  eligibility_notes: string | null;
  suggested_target_semester_id: string | null;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_comments: string | null;
  approved_by: string | null;
  approved_at: string | null;
  approved_reason: string | null;
  rejected_by: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  effective_date: string | null;
  completed_at: string | null;
  completed_by: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface TransferRequestListItem {
  request_id: string;
  student_id: string;
  student_number: string | null;
  student_name: string | null;
  transfer_type: TransferType;
  status: TransferStatus;
  eligibility_status: EligibilityStatus | null;
  current_program_name: string | null;
  target_program_name: string | null;
  submitted_at: string;
  reviewed_at: string | null;
}

export interface TransferRequestList {
  items: TransferRequestListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface TransferRequestResponse {
  request: TransferRequestView;
  actions: TransferActionRecord[];
}

export interface TransferRequestCreate {
  student_id: string;
  transfer_type: TransferType;
  target_program_id: string;
  target_batch_id: string | null;
  target_section_id: string | null;
  target_semester_id: string | null;
  target_curriculum_version_id: string | null;
  reason: string;
  supporting_documents: TransferDocument[];
  effective_date: string | null;
}

export interface TransferReview {
  action: TransferAction;
  eligibility_status: EligibilityStatus | null;
  eligibility_notes: string | null;
  suggested_target_semester_id: string | null;
  review_comments: string | null;
  approved_reason: string | null;
  rejection_reason: string | null;
  effective_date: string | null;
}

export interface TransferComplete {
  effective_date: string;
  rejection_reason?: string | null;
}

export interface SubjectEquivalency {
  equivalency_id: string;
  source_subject_id: string;
  source_subject_name: string | null;
  source_subject_code: string | null;
  target_subject_id: string;
  target_subject_name: string | null;
  target_subject_code: string | null;
  program_id: string;
  program_name: string | null;
  equivalence_type: 'same' | 'approved_equivalent' | 'repeat_required' | 'additional_required';
  source_credits: number | null;
  target_credits: number | null;
  credit_comparison: 'equal' | 'less' | 'greater' | null;
  is_active: boolean;
  created_at: string;
}

export interface InstitutionTransferSettings {
  institution_id: string;
  allow_student_transfer_requests: boolean;
  allow_staff_created_transfers: boolean;
  max_active_requests_per_student: number;
  updated_at: string | null;
}

export interface InstitutionTransferSettingsUpdate {
  allow_student_transfer_requests?: boolean;
  allow_staff_created_transfers?: boolean;
  max_active_requests_per_student?: number;
}

export interface TransferEquivalencyCreate {
  source_subject_id: string;
  target_subject_id: string;
  program_id: string;
  equivalence_type: 'same' | 'approved_equivalent' | 'repeat_required' | 'additional_required';
  source_credits: number | null;
  target_credits: number | null;
  notes: string | null;
}

export interface TransferEquivalencyList {
  items: SubjectEquivalency[];
}

export interface TransferTargetOption {
  id: string;
  name: string;
  code: string | null;
}

export interface CurrentPlacement {
  program_id: string | null;
  program_name: string | null;
  program_code: string | null;
  batch_id: string | null;
  batch_name: string | null;
  batch_code: string | null;
  section_id: string | null;
  section_name: string | null;
  section_code: string | null;
  semester_id: string | null;
  semester_name: string | null;
  curriculum_version_id: string | null;
  curriculum_version: string | null;
}