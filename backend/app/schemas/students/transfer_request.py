"""Contracts for the Student Academic Transfer System.

All request/response bodies are tenant-scoped server-side; the client never
supplies a trusted institution_id, student_id, or actor identity.
"""

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TransferType = Literal["program_transfer", "section_transfer", "semester_placement"]
TransferStatus = Literal[
    "submitted",
    "under_review",
    "eligible",
    "not_eligible",
    "approved",
    "rejected",
    "completed",
    "cancelled",
]
EligibilityStatus = Literal["eligible", "not_eligible", "manual_review", "pending"]
TransferAction = Literal["submitted", "reviewed", "approved", "rejected", "completed", "cancelled"]

MAX_REASON_LENGTH = 4000
MAX_NOTES_LENGTH = 2000
MAX_DOCUMENTS = 10


class TransferDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_name: str = Field(min_length=1, max_length=255)
    file_url: str | None = None
    file_type: str | None = Field(default=None, max_length=100)
    size_bytes: int | None = Field(default=None, ge=0)
    uploaded_at: str | None = None


class AcademicPlacement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    program_id: UUID | None = None
    program_name: str | None = None
    program_code: str | None = None
    batch_id: UUID | None = None
    batch_name: str | None = None
    batch_code: str | None = None
    section_id: UUID | None = None
    section_name: str | None = None
    section_code: str | None = None
    semester_id: UUID | None = None
    semester_name: str | None = None
    curriculum_version_id: UUID | None = None
    curriculum_version: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    is_active: bool | None = None


class TransferRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: UUID
    transfer_type: TransferType
    target_program_id: UUID
    target_batch_id: UUID | None = None
    target_section_id: UUID | None = None
    target_semester_id: UUID | None = None
    target_curriculum_version_id: UUID | None = None
    reason: str = Field(min_length=1, max_length=MAX_REASON_LENGTH)
    supporting_documents: list[TransferDocument] = Field(
        default_factory=list, max_length=MAX_DOCUMENTS
    )
    effective_date: date | None = None


class TransferRequestUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_program_id: UUID | None = None
    target_batch_id: UUID | None = None
    target_section_id: UUID | None = None
    target_semester_id: UUID | None = None
    target_curriculum_version_id: UUID | None = None
    reason: str | None = Field(default=None, min_length=1, max_length=MAX_REASON_LENGTH)
    supporting_documents: list[TransferDocument] | None = None
    effective_date: date | None = None


class TransferRequestListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    student_id: UUID
    student_number: str | None = None
    student_name: str | None = None
    transfer_type: TransferType
    status: TransferStatus
    eligibility_status: EligibilityStatus | None = None
    current_program_name: str | None = None
    target_program_name: str | None = None
    submitted_at: str
    reviewed_at: str | None = None


class TransferRequestView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: UUID
    student_id: UUID
    institution_id: UUID
    transfer_type: TransferType
    status: TransferStatus
    eligibility_status: EligibilityStatus | None = None
    current_placement: AcademicPlacement
    target_placement: AcademicPlacement
    reason: str
    supporting_documents: list[TransferDocument]
    eligibility_notes: str | None = None
    suggested_target_semester_id: UUID | None = None
    reviewed_by: UUID | None = None
    reviewed_at: str | None = None
    review_comments: str | None = None
    approved_by: UUID | None = None
    approved_at: str | None = None
    approved_reason: str | None = None
    rejected_by: UUID | None = None
    rejected_at: str | None = None
    rejection_reason: str | None = None
    effective_date: date | None = None
    completed_at: str | None = None
    completed_by: UUID | None = None
    created_by: UUID
    created_at: str
    updated_at: str


class TransferActionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_id: UUID
    action: TransferAction
    actor_user_id: UUID
    comments: str | None = None
    from_status: str | None = None
    to_status: str | None = None
    created_at: str


class TransferRequestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: TransferRequestView
    actions: list[TransferActionRecord] = Field(default_factory=list)


class TransferRequestList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TransferRequestListItem]
    total: int
    limit: int
    offset: int


class SubjectEquivalency(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equivalency_id: UUID
    source_subject_id: UUID
    source_subject_name: str | None = None
    source_subject_code: str | None = None
    target_subject_id: UUID
    target_subject_name: str | None = None
    target_subject_code: str | None = None
    program_id: UUID
    program_name: str | None = None
    equivalence_type: Literal[
        "same", "approved_equivalent", "repeat_required", "additional_required"
    ]
    source_credits: float | None = None
    target_credits: float | None = None
    credit_comparison: Literal["equal", "less", "greater"] | None = None
    is_active: bool
    created_at: str


class InstitutionTransferSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution_id: UUID
    allow_student_transfer_requests: bool
    allow_staff_created_transfers: bool
    max_active_requests_per_student: int
    updated_at: str | None = None


class TransferReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: TransferAction
    eligibility_status: EligibilityStatus | None = None
    eligibility_notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)
    suggested_target_semester_id: UUID | None = None
    review_comments: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)
    approved_reason: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)
    rejection_reason: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)
    effective_date: date | None = None


class TransferComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    effective_date: date
    rejection_reason: str | None = Field(default=None, max_length=2000)
class InstitutionTransferSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_student_transfer_requests: bool | None = None
    allow_staff_created_transfers: bool | None = None
    max_active_requests_per_student: int | None = None


class TransferEquivalencyList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SubjectEquivalency]


class TransferEquivalencyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_subject_id: UUID
    target_subject_id: UUID
    program_id: UUID
    equivalence_type: Literal[
        "same", "approved_equivalent", "repeat_required", "additional_required"
    ]
    source_credits: float | None = None
    target_credits: float | None = None
    notes: str | None = Field(default=None, max_length=2000)
