# Step 2 — Curriculum

A curriculum (study plan) says which subjects a program teaches in each program
semester. You build it as a **draft**, then **publish** it. Batches can only use
published curricula.

[← Foundations](foundations.md) · Next: [Batches and sections →](batches-and-sections.md)

## How a curriculum is organised

```
B.Tech Computer Science — curriculum "BTCS 2026", version 1.0
├── Semester 1   Programming Fundamentals (compulsory)
│                Engineering Mathematics I (compulsory)
├── Semester 2   Data Structures (compulsory)
│                Digital Logic (compulsory)
├── Semester 3   …
└── … up to Semester 8
```

The semesters here are **program semesters**: numbered stages of the degree.
They are created for you from the curriculum's semester count.

## 2.1 Create a draft curriculum

1. Open **Curriculum** → **Curriculum Versions** and select **Add Curriculum**.
2. Fill in the drawer:

   | Field | Example | Notes |
   | --- | --- | --- |
   | Program | B.Tech Computer Science | |
   | Academic Year | 2026–27 | The year this plan starts being used. |
   | Curriculum Name | BTCS 2026 | |
   | Version | `1.0` | Cannot be changed later. |
   | Total Semesters | 8 | Filled in as 2 per program year. Change it only if the program differs. |
   | Description *(optional)* | Regulation 2026 | |

3. Select **Create Curriculum**.

After saving, the **Subjects by semester** view opens for the new draft and the
program semesters (Semester 1 to Semester 8) are set up automatically. Program
semesters that already exist for the program are reused, never duplicated.

**Tip:** if a later version leaves some semesters missing, the plan shows a
**Set up N missing semesters** button that adds them in one step.

## 2.2 Add compulsory subjects to each semester

1. In **Subjects by semester**, find the **Semester 1** card.
2. Select **Add subject to Semester 1**.
3. Choose the **Subject**, for example *Programming Fundamentals (CS101)*.
4. Choose the **Subject Type**: Core, Elective, Open elective, Skill or Project.
5. Keep **Every student must take this subject** ticked for compulsory subjects.
6. Select **Save subject**.

For Greenfield College, add:

| Semester | Subject | Type | Every student must take it |
| --- | --- | --- | --- |
| 1 | Programming Fundamentals | Core | Yes |
| 1 | Engineering Mathematics I | Core | Yes |
| 2 | Data Structures | Core | Yes |
| 2 | Digital Logic | Core | Yes |

**Tip:** to fill a whole study plan at once, use **Import CSV** on the Subjects
page, choose this draft under **Place in draft curriculum**, and give each row a
`semester`. See [Importing many subjects](foundations.md).

## 2.3 Add student choices *(optional)*

Use choice groups when students pick one option from several, for example an
elective slot.

1. Add each elective subject to the semester with **Every student must take this
   subject** **unticked**. It appears under **Subjects available for choices**.
2. Select **Add choice group** and give the group a name, for example
   *Semester 5 Elective*.
3. Create the options (**Option 1**, **Option 2**, …). Give each an
   **Option Name** and tick at least one optional subject.
4. Select **Create choice group**.

When students register, they choose **exactly one option per group**, plus all
compulsory subjects.

## 2.4 Review and publish

1. Check the coverage summary. Empty semesters are flagged as warnings so you can
   review them; they do not block publishing.
2. Select **Publish study plan** and confirm.

**Important:** publishing needs at least one active subject in the plan. Once
published, the plan is **read-only**: subjects, credits and hours are frozen as
they were at that moment, so later edits to the subject catalogue do not change
what an existing batch studies.

## Changing a published curriculum

You do not edit a published plan. Instead:

1. Open the published version and select **Clone as draft** (or **Create draft
   copy**). The copy includes its subjects and choice groups.
2. Change the draft, publish it as a new version (for example `2.0`), and use it
   for new batches.
3. Use **Version History** → **Compare versions** to see added, removed and
   changed subjects between two published versions.

Batches keep the version they were created with, even if that version is later
archived. Archived versions cannot be published again.

Next: [Batches and sections →](batches-and-sections.md)
