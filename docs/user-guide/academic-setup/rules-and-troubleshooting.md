# Rules and troubleshooting

The system checks these rules on every save, so the academic structure stays
consistent. Forms explain the problem before you save; if a rule is still broken,
the save is refused with a message that names the rule and how to fix it.

[← Academic Setup guide](README.md)

## Rules at a glance

| Area | Rule |
| --- | --- |
| Codes | Department, program, subject, batch and section codes must be unique. Section codes are unique across the **whole institution**. |
| Parents | You can only choose **active** parents, for example an active department for a new program. |
| Program duration | Entered in years. It sets the default curriculum length (2 semesters per year) and the longest a batch can run. |
| Terms | A term's dates must fall inside its academic year. |
| Current period | Only one academic year and one term can be current, and they must be active. |
| Curriculum | Needs at least one active subject to publish. Published plans are read-only; change them by cloning a new draft. |
| Batch years | Start year = the year the intake academic year starts. End year ≤ start year + program duration. |
| Section term | The teaching term must fall within the batch's start and end years. |
| Capacity | A section subject's capacity ≤ its section's capacity. A section's capacity cannot drop below an active section subject's capacity. |
| Fixed after creation | Batch program, curriculum, intake year and years; section batch, program semester, term and code; curriculum version number. |

## Messages and what to do

| Message | Cause | Fix |
| --- | --- | --- |
| "Start year must be 2026, when the intake academic year starts." | The start year differs from the intake year. | Choose the right **Academic Year**; the start year follows it. |
| "End year cannot be later than 2030 for this program's duration." | The batch runs longer than the program. | Shorten the end year, or correct the program's **Duration (Years)**. |
| "An academic record already exists in this context" | A record with the same code or name already exists. | Use a different code. For sections, include the batch and semester, for example `CSE26-A-S1`. |
| "Choose an active …" | The chosen parent is inactive. | Activate the parent, or choose another one. |
| "Semester dates must fit its academic year" | A term starts or ends outside its year. | Adjust the term dates or the year dates. |
| "Add at least one subject before publishing." | The draft curriculum is empty. | Add subjects in **Subjects by semester**. |
| "Active academic year dates overlap" | Two active academic years cover the same dates. | Adjust the dates so active years do not overlap. |
| "Other active records depend on this one. Deactivate them first…" | You are deactivating a record that still has active programs, subjects, batches or sections. | Deactivate the dependent records first (programs before their department). |
| "This curriculum is published, so its subjects cannot change…" | Published curricula are read-only. | Use **Clone as draft**, change the draft and publish it as a new version. |
| "One of this section's subjects allows more students than the new capacity…" | A section subject's capacity is above the new section capacity. | Lower that subject's capacity in **Subjects by section** first. |
| "Choose a teaching term that falls within the batch's start and end years." | The term is outside the batch's years. | Pick a term inside the batch's years. |
| "Check active parents, dependent records and academic dates" | A rule was broken that has no specific message yet. | Check the rules above. This message is now rare: most rules explain themselves. |
| "This … cannot be deleted because it has linked …" | The record is in use. | Make it **Inactive** instead of deleting it. |

## Frequently asked questions

**Why does my 4-year program show 8 semesters?**
Curricula default to two program semesters per year. Change **Total Semesters**
on the draft if your program is organised differently.

**The batch end year looks wrong.**
Check the program's **Duration (Years)**. A 4-year degree entered as `8` (the
number of semesters) lets batches run for 8 years. Edit the program to fix it.

**I need to change a subject in a published curriculum.**
Clone the published version as a draft, change the draft, and publish it as a
new version. Existing batches keep their original version.

**A term I expected is missing from the section form.**
Only terms inside the batch's years are listed. A 2026–2030 batch cannot have a
section in a 2031 term.

**Can I delete a record?**
Unused academic years, terms and sections can be deleted. Records already in use
should be made **Inactive** instead, which keeps history intact.

**Do I have to create sections?**
No. Sections are optional. Create them when students need separate class groups
or when you are ready to enroll students.
