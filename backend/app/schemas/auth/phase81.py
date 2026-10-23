"""Institution-scoped staff permission request contract."""

from pydantic import BaseModel, ConfigDict, Field


class StaffPermissionGrantChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    permission_codes: list[str] = Field(min_length=1, max_length=32)
