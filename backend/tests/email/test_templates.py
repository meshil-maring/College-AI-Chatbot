import pytest

from app.services.email.templates import render_html_email, render_transactional_email


@pytest.mark.parametrize("kind", [
    "verification", "registration", "invitation_code", "password_recovery",
    "approval", "rejection", "staff_notification",
])
def test_transactional_templates_have_html_text_and_escaped_branding(kind):
    content = render_transactional_email(
        kind, institution_name="College <script>", recipient_name="Ada & Co",
        code="123456", action_url="https://app.example.edu/action#token",
    )
    assert content.subject and content.text
    assert "CollegeAIChatbot" in content.html
    assert "College &lt;script&gt;" in content.html and "<script>" not in content.html
    assert "Ada &amp; Co" in content.html
    assert "https://app.example.edu/action#token" in content.text


def test_unsafe_action_url_is_rejected():
    with pytest.raises(ValueError):
        render_html_email("Hello", "Body", action_url="javascript:alert(1)")


def test_verification_template_requires_code():
    with pytest.raises(ValueError):
        render_transactional_email("verification", institution_name="College")
