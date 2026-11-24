"""Specific, administrator-friendly messages for known Academic Setup rules.

Database guards raise fixed messages (for example 'Batch cannot run longer
than its program duration') with generic SQLSTATEs such as 23514. Each known
message maps to its own public error code and an actionable explanation.
Unknown messages keep the generic translation, so constraint names and other
database details are never exposed.

Every key must match a message raised in supabase/migrations; a test checks this.
"""

RULE = 422
CONFLICT = 409

RULE_MESSAGES: dict[str, tuple[int, str, str]] = {
    # Batch and class consistency (20261205000000_academic_setup_consistency)
    "Batch start year must match its intake academic year": (
        RULE, "ACADEMIC_BATCH_START_YEAR",
        "A batch must start in the year its intake academic year starts. Choose the matching academic year.",
    ),
    "Batch cannot run longer than its program duration": (
        RULE, "ACADEMIC_BATCH_TOO_LONG",
        "The batch's end year is later than the program's duration allows. Shorten the batch or correct the "
        "program duration.",
    ),
    "Section teaching term must fall within its batch years": (
        RULE, "ACADEMIC_SECTION_TERM_OUTSIDE_BATCH",
        "Choose a teaching term that falls within the batch's start and end years.",
    ),
    "Offering capacity cannot exceed its section capacity": (
        RULE, "ACADEMIC_OFFERING_CAPACITY",
        "A subject's capacity cannot be higher than its section's capacity.",
    ),
    "Section capacity is below a subject offering capacity": (
        RULE, "ACADEMIC_SECTION_CAPACITY",
        "One of this section's subjects allows more students than the new capacity. Lower that subject's "
        "capacity first.",
    ),
    # Curriculum lifecycle
    "An active mapped subject is required before publication": (
        RULE, "ACADEMIC_CURRICULUM_EMPTY",
        "Add at least one active subject to this curriculum before publishing it.",
    ),
    "Create a draft before publishing": (
        RULE, "ACADEMIC_CURRICULUM_NOT_DRAFT", "Only a draft curriculum can be published.",
    ),
    "Only published curricula can be archived": (
        RULE, "ACADEMIC_CURRICULUM_NOT_PUBLISHED", "Only a published curriculum can be archived.",
    ),
    "Published curriculum mappings are immutable": (
        RULE, "ACADEMIC_CURRICULUM_LOCKED",
        "This curriculum is published, so its subjects cannot change. Clone it as a draft to make changes.",
    ),
    "Published curriculum versions are immutable": (
        RULE, "ACADEMIC_CURRICULUM_LOCKED",
        "This curriculum is published and can no longer be edited. Clone it as a draft to make changes.",
    ),
    "Complete every subject option before publishing": (
        RULE, "ACADEMIC_CHOICES_INCOMPLETE",
        "Finish every subject choice group before publishing: each option needs at least one subject.",
    ),
    # Relationships between records
    "Curriculum and program semester must match": (
        RULE, "ACADEMIC_RELATIONSHIP_INVALID",
        "The program semester must belong to the same program as the curriculum.",
    ),
    "Matching published curriculum required": (
        RULE, "ACADEMIC_RELATIONSHIP_INVALID",
        "Choose a published curriculum of the same program.",
    ),
    "Section must use its cohort program": (
        RULE, "ACADEMIC_RELATIONSHIP_INVALID",
        "The program semester must belong to the batch's program.",
    ),
    "Offering must match section semester and assigned curriculum": (
        RULE, "ACADEMIC_RELATIONSHIP_INVALID",
        "Choose a subject from this section's curriculum and program semester.",
    ),
    # Active parents and dependent records
    "Active academic ancestry required": (
        RULE, "ACADEMIC_PARENT_INACTIVE",
        "A record this depends on is inactive. Activate it first, or choose an active one.",
    ),
    "Active academic parents required": (
        RULE, "ACADEMIC_PARENT_INACTIVE",
        "A record this depends on is inactive. Activate it first, or choose an active one.",
    ),
    "Academic parent missing": (
        RULE, "ACADEMIC_PARENT_INACTIVE", "The record this belongs to no longer exists. Refresh and try again.",
    ),
    "Active department required": (
        RULE, "ACADEMIC_PARENT_INACTIVE", "Choose an active department.",
    ),
    "Active institution required": (
        RULE, "ACADEMIC_INSTITUTION_INACTIVE", "Your institution is not active, so academic records cannot change.",
    ),
    "Active institution and organization required": (
        RULE, "ACADEMIC_INSTITUTION_INACTIVE",
        "Your institution or organization is not active, so academic records cannot change.",
    ),
    "Deactivate dependent academic records first": (
        CONFLICT, "ACADEMIC_HAS_ACTIVE_DEPENDENTS",
        "Other active records depend on this one. Deactivate them first, for example its programs, subjects, "
        "batches or sections.",
    ),
    "Deactivate dependent degree programs first": (
        CONFLICT, "ACADEMIC_HAS_ACTIVE_DEPENDENTS", "Deactivate this department's programs first.",
    ),
    "Deactivate dependent sections first": (
        CONFLICT, "ACADEMIC_HAS_ACTIVE_DEPENDENTS", "Deactivate the sections that use this record first.",
    ),
    "Remove active subject assignments first": (
        CONFLICT, "ACADEMIC_HAS_ACTIVE_DEPENDENTS", "Remove or deactivate this section's subjects first.",
    ),
    "Offering has registered students": (
        CONFLICT, "ACADEMIC_IN_USE", "Students have registered for this subject, so it cannot change this way.",
    ),
    "Section has assigned students": (
        CONFLICT, "ACADEMIC_IN_USE", "Students are assigned to this section, so it cannot change this way.",
    ),
    "Remove this subject from draft options before changing its status": (
        CONFLICT, "ACADEMIC_IN_USE", "Remove this subject from its choice group before changing its status.",
    ),
    # Calendar
    "Semester must fit active academic year": (
        RULE, "ACADEMIC_TERM_OUTSIDE_YEAR", "A term's dates must fall inside an active academic year.",
    ),
    "Year dates exclude existing semesters": (
        RULE, "ACADEMIC_YEAR_EXCLUDES_TERMS",
        "The new dates would leave some of this year's terms outside it. Adjust those terms first.",
    ),
    "Academic name and code must be nonblank": (
        RULE, "ACADEMIC_INPUT_INVALID", "Name and code cannot be blank.",
    ),
    # Subject choice groups
    "Edit option groups only in a matching draft curriculum": (
        RULE, "ACADEMIC_CURRICULUM_LOCKED", "Choice groups can only be changed in a draft curriculum.",
    ),
    "Option subjects must be active optional mappings in this semester": (
        RULE, "ACADEMIC_CHOICES_INVALID",
        "Options can only use active subjects of this semester that are not compulsory.",
    ),
    "Subject already belongs to another choice group": (
        CONFLICT, "ACADEMIC_CHOICES_INVALID", "This subject is already in another choice group.",
    ),
    "Every option requires subjects": (
        RULE, "ACADEMIC_CHOICES_INVALID", "Every option needs at least one subject.",
    ),
    "Provide two or more complete options": (
        RULE, "ACADEMIC_CHOICES_INVALID", "A choice group needs at least two complete options.",
    ),
    # Student enrollment
    "Assign only approved active students": (
        RULE, "ENROLLMENT_STUDENT_INELIGIBLE", "Only approved, active students can be assigned to a section.",
    ),
    "Student already belongs to another batch; a transfer requires a separate workflow": (
        CONFLICT, "ENROLLMENT_OTHER_BATCH",
        "This student already belongs to another batch. Use Student Transfers to move them.",
    ),
}


def rule_message(code: str, message: str) -> tuple[int, str, str] | None:
    """Return the specific translation for a known rule violation, if any."""
    if code not in {"23514", "23503", "22023"}:
        return None
    return RULE_MESSAGES.get((message or "").strip())
