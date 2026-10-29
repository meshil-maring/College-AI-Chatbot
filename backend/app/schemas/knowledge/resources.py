"""Strict shared resource drafts, review commands and safe response projections."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AudienceRole = Literal['student', 'staff', 'faculty', 'admin']
ReviewAction = Literal['submit', 'request_changes', 'approve', 'publish', 'unpublish']


class Audience(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['public', 'institution', 'roles']
    roles: list[AudienceRole] = Field(default_factory=list, max_length=4)

    @model_validator(mode='after')
    def validate_roles(self):
        if len(self.roles) != len(set(self.roles)):
            raise ValueError('Choose each audience role once.')
        if self.mode != 'roles' and self.roles:
            raise ValueError('Public and institution audiences cannot select roles.')
        return self


class DraftFields(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    source_type: str | None = Field(default=None, min_length=1, max_length=50)
    audience: Audience | None = None
    effective_from: date | None = None
    effective_until: date | None = None

    @field_validator('source_type')
    @classmethod
    def reject_canonical_type(cls, value):
        if value in {'faq', 'notice'}:
            raise ValueError('Use the existing FAQ or notice editor.')
        return value

    @model_validator(mode='after')
    def validate_dates(self):
        if self.effective_from and self.effective_until and self.effective_until < self.effective_from:
            raise ValueError('The end date must follow the start date.')
        return self

    def database_fields(self):
        fields = self.model_dump(mode='json', exclude_unset=True, exclude={'audience'})
        if 'audience' in self.model_fields_set:
            if self.audience is None:
                raise ValueError('An audience selection cannot be null.')
            fields['visibility'] = {'public': 'public', 'institution': 'authenticated', 'roles': 'restricted'}[self.audience.mode]
            fields['audience_roles'] = self.audience.roles
        return fields


class CreateResource(DraftFields):
    title: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=50)


class UpdateDraft(DraftFields):
    expected_version: int = Field(ge=1)

    def database_fields(self):
        return {key: value for key, value in super().database_fields().items() if key != 'expected_version'}


class ReviewCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)
    expected_policy: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=5000)


class RetryIndex(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)
    document_version_id: UUID


class ResourceFile(BaseModel):
    document_id: UUID
    document_version_id: UUID
    original_filename: str
    file_type: str
    version_number: int
    file_size_bytes: int | None = None
    indexing_status: Literal['queued', 'processing', 'indexed', 'failed'] | None = None


class ResourceItem(BaseModel):
    knowledge_source_id: UUID
    title: str
    description: str | None = None
    source_type: str
    visibility: Literal['public', 'authenticated', 'restricted']
    effective_from: date | None = None
    effective_until: date | None = None
    policy_version: int
    audience_roles: list[AudienceRole] = Field(default_factory=list)
    documents: list[ResourceFile] = Field(default_factory=list)


class RevisionItem(ResourceItem):
    revision_id: UUID
    institution_id: UUID
    revision_number: int
    revision_version: int
    lifecycle_status: str
    created_by_user_id: UUID
    reviewed_by_user_id: UUID | None = None
    approved_by_user_id: UUID | None = None
    review_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class ResourceList(BaseModel):
    items: list[ResourceItem]
    total: int


class RevisionList(BaseModel):
    items: list[RevisionItem]
    total: int
