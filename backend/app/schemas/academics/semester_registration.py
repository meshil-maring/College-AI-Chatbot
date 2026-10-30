"""Whole-option curriculum choices and server-assigned semester registration."""

from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.academics.academic_setup import AcademicModel, Name


class SubjectOption(AcademicModel):
    name: Name
    curriculum_subject_ids: list[UUID] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_subjects(self):
        if len(set(self.curriculum_subject_ids)) != len(self.curriculum_subject_ids):
            raise ValueError("A subject can appear only once in an option")
        return self


class ChoiceGroupWrite(AcademicModel):
    curriculum_version_id: UUID
    program_semester_id: UUID
    name: Name
    options: list[SubjectOption] = Field(min_length=2, max_length=20)

    @model_validator(mode="after")
    def unique_names(self):
        names = [option.name.strip().casefold() for option in self.options]
        if len(set(names)) != len(names):
            raise ValueError("Option names must be unique within a group")
        return self


class SemesterAssignment(AcademicModel):
    student_id: UUID
    academic_section_id: UUID


class SemesterSelection(AcademicModel):
    selected_option_ids: list[UUID] = Field(max_length=32)

    @model_validator(mode="after")
    def unique_options(self):
        if len(set(self.selected_option_ids)) != len(self.selected_option_ids):
            raise ValueError("Choose each option only once")
        return self
