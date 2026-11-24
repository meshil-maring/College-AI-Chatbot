# Steps 3 and 4 — Batches and sections

A **batch** groups the students admitted to a program in the same intake and
fixes which published curriculum they follow. **Sections** split a batch into
class groups for a particular program semester and teaching term, and **section
subjects** decide what each class group can study.

[← Curriculum](curriculum.md) · Next: [Student enrollment →](student-enrollment.md)

## 3. Create a batch

You need a published curriculum for the program first (see
[Curriculum](curriculum.md)).

1. Open **Batches** and select **Add Batch**.
2. Fill in the drawer:

   | Field | Example | Notes |
   | --- | --- | --- |
   | Batch Name | CSE 2026 | |
   | Batch Code | `CSE26` | |
   | Program | B.Tech Computer Science | |
   | Curriculum Version | BTCS 2026 · v1.0 | Selected for you when the program has only one published curriculum. |
   | Academic Year | 2026–27 | The intake year. The current active year is suggested. |
   | Start Year | 2026 | Filled in from the intake academic year; you cannot change it. |
   | End Year | 2030 | Filled in as start year + program duration. |
   | Expected Student Count *(optional)* | 60 | A planning figure, not a limit. |
   | Description *(optional)* | | |
   | Status | Active | Active batches accept student enrollment. |

3. Select **Create Batch**.

**Important:**

- The start year always matches the year the intake academic year starts.
- The end year can be **earlier** than the default, for example for a
  lateral-entry batch that joins in the second year (2027–2030), but never
  **later** than the program duration allows.
- After creation, the program, curriculum, intake year and years cannot change.
  The batch keeps its curriculum even if that version is later archived.

After saving, the batch list shows **Set up sections**. It opens the section
form for you; it does not create anything by itself.

## 4.1 Create a section

Sections are **optional**. Create them when students in a batch need separate
class groups, and for each program semester they reach.

1. Open **Academic Sections** and select **Add Section** (or use **Set up
   sections** on the batch).
2. Fill in the drawer:

   | Field | Example | Notes |
   | --- | --- | --- |
   | Section Name | Section A | |
   | Section Code | `A` | Unique within the batch's program semester. Other batches, and this batch's other semesters, can also use `A`. |
   | Batch | CSE 2026 | Program and Batch Academic Year fill in from the batch. |
   | Program Semester | Semester 1 | The degree stage these students are in. |
   | Teaching Term | Odd Term (2026–27) | Only terms inside the batch's years are offered. |
   | Maximum Capacity *(optional)* | 60 | |
   | Description *(optional)* | | |

3. Select **Create Section**.

For Greenfield College, create one section per term of the first year:

| Section Code | Program Semester | Teaching Term | Capacity |
| --- | --- | --- | --- |
| `A` | Semester 1 | Odd Term 2026–27 | 60 |
| `A` | Semester 2 | Even Term 2026–27 | 60 |

The batch, program semester, term and code cannot be changed after creation.
The name, capacity and description can.

## 4.2 Choose the subjects for each section

Section subjects make curriculum subjects available to a section's students.
Only subjects from the batch's curriculum, in the section's program semester, can
be chosen.

1. Open **Subjects by section**: use **Choose subjects by section** in the setup
   guide after creating a section, or the overview's **Manage subjects by
   section** quick action.
2. Select **Add Section Subject**.
3. Choose the **Section**, then the **Subject**.
4. Optionally set a **Maximum Capacity**. It cannot be higher than the section's
   capacity.
5. Select **Create Section Subject**.

For Greenfield College:

| Section | Subjects |
| --- | --- |
| Section A, Semester 1 | Programming Fundamentals, Engineering Mathematics I |
| Section A, Semester 2 | Data Structures, Digital Logic |

**Important:** every compulsory subject, and every subject a student may pick in
a choice group, must be made available to the section. Otherwise students cannot
finish their registration.

## Changing capacity later

- A section subject's capacity cannot exceed its section's capacity.
- A section's capacity cannot be lowered below the capacity of any of its active
  section subjects. Lower the section subjects first, then the section.

## Starting the next academic year

At the end of a year, **Roll over to next year** on the **Academic Calendar**
page does the yearly setup in one step:

1. Choose the year to copy from (the current year is selected).
2. Review the preview:
   - **Calendar:** the next academic year and its terms, with dates moved
     forward by one year (for example *2026 - 2027* becomes *2027 - 2028*).
   - **Sections:** each active batch's sections continue into their next
     semesters. With two terms a year, Section A of Semester 1 (Odd Term)
     becomes Section A of Semester 3 in next year's Odd Term, with the same code
     and capacity. Every active subject of that semester in the batch's
     curriculum is made available to the new section.
   - **Not continued:** batches that end before next year, or whose curriculum
     has no further semesters.
3. Select **Roll over**. Records that already exist are reused, so running it
   again never creates duplicates. If it stops part-way, select **Retry**: it
   continues with whatever is still missing.

Afterwards, review the new sections and adjust any subjects, then assign
students in **Student Enrollment**.

Next: [Student enrollment →](student-enrollment.md)
