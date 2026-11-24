# Step 1 — Foundations

Foundations are the building blocks every later step refers to: departments,
programs, the academic calendar and the subject catalogue.

[← Academic Setup guide](README.md) · Next: [Curriculum →](curriculum.md)

## 1.1 Create a department

A department owns its programs and subjects.

1. Open **Departments** and select **Add Department**.
2. Fill in the drawer:

   | Field | Example | Notes |
   | --- | --- | --- |
   | Name | Computer Science and Engineering | Shown everywhere the department appears. |
   | Code | `CSE` | Short and unique in your institution, up to 32 characters. |
   | Description *(optional)* | Undergraduate and postgraduate computing programs | |
   | Status | Active | Only active departments can receive new programs and subjects. |

3. Select **Create Department**.

**Tip:** once the department is active, you can open it and use **Add a Head of
Department** to appoint an existing faculty member.

## 1.2 Create a program

A program is a degree, diploma or certificate offered by a department.

1. Open **Programs** and select **Add Program**.
2. Fill in the drawer:

   | Field | Example | Notes |
   | --- | --- | --- |
   | Program Name | B.Tech Computer Science | |
   | Program Code | `BTCS` | |
   | Department | Computer Science and Engineering | Only active departments are listed. |
   | Degree Type | B.Tech | |
   | Duration (Years) | 4 | Use years, not semesters. A 4-year degree is `4`, not `8`. The form warns you if a duration looks like a semester count. |
   | Total Credits *(optional)* | 160 | |
   | Program Description *(optional)* | | |

3. Select **Create Program**.

**Important:** the duration decides how many program semesters the curriculum
gets by default (2 per year) and the longest a batch can run. Enter it in
**years**.

## 1.3 Create the academic year

The academic year is shared by every department and program.

1. Open **Academic Calendar** → **Academic Years** and select
   **Add Academic Year**.
2. Fill in the drawer:

   | Field | Example |
   | --- | --- |
   | Name | 2026–27 |
   | Code | `AY2026` |
   | Start Date | 1 August 2026 |
   | End Date | 31 July 2027 |
   | Current | Tick this if teaching is happening in this year now |

3. Select **Create Academic Year**.

Only one academic year can be current at a time, and the current year must be
active.

## 1.4 Add the academic terms

Terms are the dated teaching periods inside the year.

1. Open **Academic Calendar** → **Terms**, or use **Add Term** on the academic
   year.
2. Create one record per teaching period:

   | Field | Odd Term | Even Term |
   | --- | --- | --- |
   | Academic Year | 2026–27 | 2026–27 |
   | Name | Odd Term | Even Term |
   | Code | `ODD26` | `EVEN27` |
   | Term Number | 1 | 2 |
   | Start Date | 1 Aug 2026 | 30 Jan 2027 |
   | End Date | 29 Jan 2027 | 31 Jul 2027 |

3. Select **Create Term** for each one.

**Important:** a term's dates must fall inside its academic year. A term is a
calendar period for *everyone*; it is not the same as "Semester 1" of a degree.
Students in Semester 1 and Semester 3 can both study during the Odd Term.

## 1.5 Add subjects

Subjects are reusable. Create each subject once in its department's catalogue,
then place it in one or more curricula.

1. Open **Subjects** and select **Add Subject**.
2. Fill in the drawer:

   | Field | Example | Notes |
   | --- | --- | --- |
   | Subject Name | Programming Fundamentals | |
   | Subject Code | `CS101` | |
   | Department | Computer Science and Engineering | |
   | Credits *(optional)* | 4 | Decimals such as `1.5` are kept exactly. |
   | Lecture Hours (L) *(optional)* | 3 | Weekly hours. |
   | Tutorial Hours (T) *(optional)* | 1 | |
   | Practical Hours (P) *(optional)* | 2 | |
   | Subject Description *(optional)* | | |

3. Select **Create Subject**.

For Greenfield College, add these four subjects:

| Code | Subject | Credits | L-T-P |
| --- | --- | --- | --- |
| CS101 | Programming Fundamentals | 4 | 3-1-2 |
| MA101 | Engineering Mathematics I | 4 | 3-1-0 |
| CS102 | Data Structures | 4 | 3-1-2 |
| CS103 | Digital Logic | 3 | 3-0-2 |

### Importing many subjects from a CSV file

Instead of adding subjects one by one, select **Import CSV** on the Subjects page.

1. Choose the **Department**.
2. Optionally choose a draft curriculum under **Place in draft curriculum**. Rows
   with a `semester` value are then also added to that semester of the plan.
3. Select **Choose CSV file**. Use **Download template** to see the format:

   ```
   code,name,credits,L,T,P,semester,type,required,description
   CS101,Programming Fundamentals,4,3,1,2,1,core,yes,
   CS205,Machine Learning,3,3,0,0,5,elective,no,Semester 5 elective option
   ```

4. Review the preview. Rows with problems show the reason and are skipped.
   Subjects whose code already exists in the department are reused, not
   duplicated.
5. Select **Import N rows**. If some rows fail, the button changes to **Retry
   N failed rows** and repeats only those.

`type` defaults to `core`. `required` defaults to `yes`, except for electives,
which default to `no` so they can be used in choice groups.

## Check before moving on

The **Setup guide** marks Foundations as ready when the selected program has
at least one active subject, an active academic year, and a teaching term in that
year. If it shows **Add teaching terms**, add the terms from step 1.4.

Next: [Curriculum →](curriculum.md)
