"""Strict Faculty assessment commands; authority is never accepted in payloads."""

from datetime import date, time
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Score = Annotated[Decimal, Field(ge=0, max_digits=8, decimal_places=2, allow_inf_nan=False)]
MarkStatus = Literal['present', 'absent', 'exempt', 'not_attempted', 'missing']


class Command(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class TestInput(Command):
    title: str = Field(min_length=1, max_length=160)
    test_type: str = Field(min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=4000)
    max_marks: Score = Field(gt=0)
    passing_marks: Score | None = None
    scheduled_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    duration_minutes: int | None = Field(default=None, ge=1, le=1440)

    @model_validator(mode='after')
    def consistent(self):
        if self.passing_marks is not None and self.passing_marks > self.max_marks:
            raise ValueError('Passing marks cannot exceed maximum marks')
        if bool(self.start_time) != bool(self.end_time) or (
            self.start_time and (not self.scheduled_date or self.end_time <= self.start_time)
        ):
            raise ValueError('Provide a date and valid start/end times')
        if any(t and t.tzinfo for t in (self.start_time, self.end_time)):
            raise ValueError('Use local academic time without a timezone offset')
        return self


class TestUpdate(TestInput):
    expected_version: int = Field(ge=1)


class MarkInput(Command):
    roster_id: UUID
    mark_status: MarkStatus
    scored_marks: Score | None = None
    remarks: str | None = Field(default=None, max_length=1000)

    @model_validator(mode='after')
    def explicit_score(self):
        if (self.mark_status == 'present') != (self.scored_marks is not None):
            raise ValueError('Present requires a score; other statuses require empty marks')
        return self


class MarksCommand(Command):
    expected_version: int = Field(ge=1)
    rows: list[MarkInput] = Field(min_length=1, max_length=500)

    @model_validator(mode='after')
    def unique_rosters(self):
        if len({r.roster_id for r in self.rows}) != len(self.rows):
            raise ValueError('Duplicate roster identity')
        return self


class Transition(Command):
    expected_version: int = Field(ge=1)
    action: Literal['schedule', 'start', 'complete', 'submit', 'return_marks', 'publish', 'lock', 'cancel']


class Correction(MarksCommand):
    reason: str = Field(min_length=10, max_length=1000)


class ImportCorrection(Command):
    expected_updated_at: str = Field(min_length=1, max_length=64)
    data: dict[str, str] = Field(max_length=20)


class ImportCommit(Command):
    expected_version: int = Field(ge=1)
    expected_updated_at: str = Field(min_length=1, max_length=64)
