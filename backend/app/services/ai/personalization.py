"""Pure private-record question detection and legacy prompt redaction.

These guards never load a student record or call an academic service. They
remain part of public/chat privacy handling after academic modules retire.
"""

import re
from enum import Enum


class PersonalizationIntent(str, Enum):
    """Controlled vocabulary of personal-data intents."""

    ATTENDANCE = "attendance"
    TEST_RESULTS = "test_results"
    ACADEMIC_RESULTS = "academic_results"
    PERFORMANCE = "performance"
    COURSES = "courses"
    PROFILE = "profile"


_TOPIC_RULES: tuple[tuple[PersonalizationIntent, re.Pattern], ...] = (
    (
        PersonalizationIntent.ATTENDANCE,
        re.compile(
            r"(?i)\battendance?\b|\battend(ed|ing)?\b|\babsent\b|"
            r"\bhow many classes\b|\bclasses? (attended|missed|present|absent)\b"
        ),
    ),
    (
        PersonalizationIntent.TEST_RESULTS,
        re.compile(
            r"(?i)\btest (results?|scores?|marks?|grades?)\b|"
            r"\bexam (results?|scores?)\b|"
            r"\bhow did i (do|perform)\b|"
            r"\bperform(ed|ance)? in (my |the )?(recent |latest )?tests?\b|"
            r"\btest percentages?\b|\btests? (scored|marks?|scores?)\b|"
            r"\b(internal|midterms?|mid-terms?|quizzes?|assignments?) tests?\b"
        ),
    ),
    (
        PersonalizationIntent.ACADEMIC_RESULTS,
        re.compile(
            r"(?i)\b(academic )?results?\b|\bresult summaries?\b|"
            r"\bsgpa\b|\bcgpa\b|\bgpa\b|\bconsolidated\b|"
            r"\bsemester (results?|grades?|gpa)\b|\boverall (marks?|grades?)\b"
        ),
    ),
    (
        PersonalizationIntent.PERFORMANCE,
        re.compile(
            r"(?i)\bperformance\b|\boverall standing\b|\bpercentages?\b|"
            r"\bmarks?\b|\bgrades?\b|\bstanding\b|\bprogress\b|\bcurrent academic\b"
        ),
    ),
    (
        PersonalizationIntent.COURSES,
        re.compile(
            r"(?i)\bcourses?\b|\bsubjects?\b|\benroll(ed|ment)?\b|"
            r"\bassociated with\b|\bcurriculum\b"
        ),
    ),
    (
        PersonalizationIntent.PROFILE,
        re.compile(
            r"(?i)\bprofile\b|\bprogram\b|\badmission details?\b|\bstudent number\b|"
            r"\bmy (details|info|information)\b"
        ),
    ),
)

_SELF_REFERENCE_PATTERN = re.compile(
    r"(?i)\bmy\b|\bmine\b|"
    r"\bhow (did|have|well|many|much) i\b|"
    r"\bhave i\b|\bam i\b|\bdid i\b|\bdo i\b|\bwill i\b|\bwould i\b|"
    r"\bi (have|had|attended|scored|got|received|missed|took|taken|am|was|"
    r"went|failed|passed)\b|"
    r"\bstudent number\b"
)

# "my attendance", "mine", "I scored..." — signals the user owns the data.
_STRONG_SELF_REFERENCE_PATTERN = re.compile(
    r"(?i)\bmy\b|\bmine\b|"
    r"\bi (have|had|attended|scored|got|received|missed|took|taken|was|"
    r"went|failed|passed)\b|"
    r"\bhow (did|have|well|many|much) i\b"
)

# Policy/rule/process vocabulary — an "attendance" question phrased as a rule
# question ("What attendance do I need...?") is general college knowledge, not
# a request for the student's own record.
_POLICY_SIGNAL_PATTERN = re.compile(
    r"(?i)\bneed\b|\bneeded\b|\brequired\b|\brequires?\b|\brequirements?\b|"
    r"\bmandatory\b|\bminimum\b|\bpolicy\b|\bregulations?\b|\brules?\b|"
    r"\ballowed\b|\beligible\b|\beligibility\b|\bcriteria\b|\blevel\b|"
    r"\bdeadline\b|\bsyllabus\b|\bprocedure\b|\bprocess\b|\bhow to\b|\bhow do i\b"
)


def classify_personalization_question(
    user_query: str | None,
) -> PersonalizationIntent | None:
    """Return the personalization intent for a user question, or None.

    ``None`` means the question is treated as a general college-knowledge
    question and no student data is loaded.
    """
    if not user_query or not user_query.strip():
        return None
    text = " ".join(user_query.split())
    topics = [intent for intent, pattern in _TOPIC_RULES if pattern.search(text)]
    if not topics:
        return None
    if not _SELF_REFERENCE_PATTERN.search(text):
        return None
    # Policy vocabulary with only weak self-reference stays general.
    if _POLICY_SIGNAL_PATTERN.search(
        text
    ) and not _STRONG_SELF_REFERENCE_PATTERN.search(text):
        return None
    return topics[0]


_REDACTED_BLOCK = (
    "<authorized_student_data>"
    "[REDACTED - student data is not exposed through debug diagnostics]"
    "</authorized_student_data>"
)

_STUDENT_BLOCK_PATTERN = re.compile(
    r"<authorized_student_data>.*?</authorized_student_data>", re.DOTALL
)


def redact_student_data(text: str | None) -> str | None:
    """Redact the authorized student data block from any diagnostic text.

    Returns the text with every ``<authorized_student_data>...</authorized_student_data>``
    block replaced by a redacted marker. Text without the block is returned
    unchanged. This is the single gate between the generation prompt and any
    debug/diagnostic/log consumer.
    """
    if text is None:
        return None
    return _STUDENT_BLOCK_PATTERN.sub(_REDACTED_BLOCK, text)


def prompt_contains_student_data(text: str | None) -> bool:
    """True when the supplied prompt text contains the student data block."""
    return bool(text) and bool(_STUDENT_BLOCK_PATTERN.search(text))
