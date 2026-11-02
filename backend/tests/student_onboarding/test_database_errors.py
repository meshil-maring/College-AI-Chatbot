from unittest.mock import Mock

import pytest
from postgrest.exceptions import APIError

from app.core.errors import AppError
from app.services.invitations.student_onboarding_common import database


@pytest.mark.parametrize(
    "code",
    ["42P01", "42703", "42883", "PGRST202", "PGRST204", "PGRST205"],
)
def test_missing_onboarding_schema_has_actionable_error(code):
    failure = APIError({"code": code, "message": "database detail"})

    with pytest.raises(AppError) as error:
        database(Mock(side_effect=failure))

    assert error.value.status_code == 503
    assert error.value.code == "STUDENT_ONBOARDING_SCHEMA_UNAVAILABLE"
    assert "student onboarding migration" in error.value.message
    assert "database detail" not in error.value.message
