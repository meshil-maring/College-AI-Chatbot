# Academic Setup guide

Academic Setup describes how your institution teaches: who offers which degree,
when teaching happens, what students study in each semester, and which class
group each student belongs to. Students, faculty and the AI assistant all rely
on this structure, so set it up before inviting students.

**Who can use it:** institution administrators. Every change is recorded in the
activity history shown on the Academic Setup overview.

## Key terms

Several terms sound similar. The difference matters, so read these first.

| Term | What it means | Example |
| --- | --- | --- |
| **Department** | An academic unit that owns programs and subjects. | Computer Science and Engineering |
| **Program** | A degree or diploma offered by a department, with a duration. | B.Tech Computer Science, 4 years |
| **Academic year** | A dated institution-wide year. | 2026–27, 1 Aug 2026 – 31 Jul 2027 |
| **Academic term** | A dated teaching period inside an academic year. It answers *when* classes run. | Odd Term, 1 Aug 2026 – 29 Jan 2027 |
| **Subject** | A reusable course in a department's catalogue. | Data Structures, 4 credits |
| **Program semester** | A numbered stage of a degree. It answers *where* a student is in the program. | Semester 3 of B.Tech |
| **Curriculum** (study plan) | The subjects a program teaches in each program semester. It is drafted, then published. | B.Tech CS 2026, version 1.0 |
| **Batch** | Students admitted to a program in the same intake, following one published curriculum. | CSE 2026 (2026–2030) |
| **Section** | A class group inside a batch for one program semester and one academic term. | Section A, Semester 1, Odd Term |
| **Section subject** | A curriculum subject made available to a section's students. | Data Structures for Section A |

**Important:** an *academic term* is a calendar period; a *program semester* is a
stage of the degree. A student in **Semester 3** studies during a dated term such
as **Odd Term 2027–28**. Keep them separate.

## The setup flow

Work through the steps in this order. Each step depends on the ones before it.
The **Setup guide** panel on the Academic Setup overview tracks your progress and
shows the recommended next step.

```
1. Foundations      Department → Program → Academic year → Terms → Subjects
2. Curriculum       Draft study plan → Subjects per semester → Publish
3. Batches          Intake batch with its published curriculum
4. Classes          Sections → Subjects available to each section
5. Enrollment       Assign students to sections → Students register subjects
```

| Step | Guide page |
| --- | --- |
| 1. Foundations | [Foundations](foundations.md) |
| 2. Curriculum | [Curriculum](curriculum.md) |
| 3–4. Batches and classes | [Batches and sections](batches-and-sections.md) |
| 5. Enrollment | [Student enrollment](student-enrollment.md) |
| Rules and problems | [Rules and troubleshooting](rules-and-troubleshooting.md) |

## Quickest way to start

**Quick Setup** (a button on the Academic Setup overview) walks through steps 1–4
for one program on a single page: department → program → academic year and
terms → draft curriculum → subjects from a CSV file → publish → batch and its
first-year sections. Each step either reuses an existing record or creates a
new one, and saves before moving on, so you can stop and come back.

Each following year, **Roll over to next year** on the Academic Calendar page
creates the next year's calendar and continues every active batch into its next
semesters (see [Batches and sections](batches-and-sections.md)).

The pages below explain each step in detail.

## Getting there

1. Sign in as an institution administrator.
2. Open **Academic Setup** from the admin sidebar.
3. The overview shows one card per area (**Departments**, **Programs**,
   **Academic Calendar**, **Subjects**, **Curriculum**, **Batches**,
   **Academic Sections**) with active and inactive counts, plus the
   **Setup guide** and recent activity.
4. Use a card's **Manage …** link, the sidebar, or the search box to open an area.

## The example used throughout

**Greenfield College** is setting up its first degree:

- Department: **Computer Science and Engineering** (code `CSE`)
- Program: **B.Tech Computer Science** (code `BTCS`), 4 years
- Academic year: **2026–27**, 1 August 2026 to 31 July 2027
- Terms: **Odd Term** (1 Aug 2026 – 29 Jan 2027) and **Even Term**
  (30 Jan 2027 – 31 Jul 2027)
- Four first-year subjects, a published curriculum, the **CSE 2026** batch,
  and **Section A** for Semester 1

By the end of the guide, a student in Section A can register for their subjects.

## Quick checklist

- [ ] Department created and active
- [ ] Program created with the correct duration in years
- [ ] Academic year and its terms created, with dates inside the year
- [ ] Subjects added to the department's catalogue
- [ ] Curriculum drafted, subjects mapped to semesters, then published
- [ ] Batch created with the published curriculum
- [ ] Sections created and section subjects chosen
- [ ] Students assigned to sections
