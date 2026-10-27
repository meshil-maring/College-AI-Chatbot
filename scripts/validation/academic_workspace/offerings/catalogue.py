"""Complete fictional degree plans, retained in the application's institution."""

from datetime import date


PROGRAMS = [
    ("CS", "Computer Science", "B.Tech Computer Science", "B.Tech", 60, [
        ["Programming Fundamentals", "Engineering Mathematics I", "Programming Laboratory"],
        ["Data Structures", "Engineering Mathematics II", "Object Oriented Programming"],
        ["Computer Organization", "Discrete Mathematics", "Web Development"],
        ["Design and Analysis of Algorithms", "Database Management", "Database Laboratory"],
        ["Operating Systems", "Computer Networks", "Artificial Intelligence"],
        ["Software Engineering", "Theory of Computation", "Cloud Computing"],
        ["Machine Learning", "Information Security", "Industrial Internship"],
        ["Distributed Systems", "Professional Ethics", "Final Year Project"],
    ]),
    ("EC", "Electronics and Communication", "B.Tech Electronics and Communication", "B.Tech", 60, [
        ["Basic Electronics", "Engineering Mathematics I", "Electronics Laboratory"],
        ["Circuit Theory", "Engineering Mathematics II", "Circuit Simulation"],
        ["Analog Electronics", "Signals and Systems", "Analog Laboratory"],
        ["Digital Electronics", "Electromagnetic Theory", "Digital Design Laboratory"],
        ["Microprocessors", "Communication Systems", "Embedded Systems"],
        ["Digital Signal Processing", "VLSI Design", "Internet of Things"],
        ["Wireless Communication", "Control Systems", "Industrial Internship"],
        ["Optical Communication", "Professional Ethics", "Final Year Project"],
    ]),
    ("MA", "Mathematics", "B.Sc Mathematics", "B.Sc", 40, [
        ["Differential Calculus", "Classical Algebra", "Mathematical Computing"],
        ["Integral Calculus", "Trigonometry", "Computational Mathematics"],
        ["Real Analysis I", "Linear Algebra I", "Probability"],
        ["Real Analysis II", "Linear Algebra II", "Statistics"],
        ["Abstract Algebra", "Complex Analysis", "Operations Research"],
        ["Topology", "Differential Equations", "Mathematics Project"],
    ]),
]


def calendar(writer, prefix):
    """Match the institution's existing August-to-July academic calendar."""
    result = {}
    for year in range(2025, 2030):
        year_id = writer.save("academic_years", {
            "name": f"{year}-{year + 1}", "code": f"{prefix}-AY{year}",
            "start_date": f"{year}-08-01", "end_date": f"{year + 1}-07-31",
        })
        terms = []
        for number, start, end in [
            (1, date(year, 8, 1), date(year + 1, 1, 31)),
            (2, date(year + 1, 2, 1), date(year + 1, 7, 31)),
        ]:
            terms.append(writer.save("semesters", {
                "academic_year_id": year_id, "name": f"{year}-{year + 1} Term {number}",
                "code": f"{prefix}-{year}-T{number}", "semester_number": number,
                "start_date": start.isoformat(), "end_date": end.isoformat(),
            }))
        result[year] = (year_id, terms)
    return result


def subject_type(stage, index, total):
    if index < 2:
        return "core"
    if stage == total:
        return "project"
    return ["skill", "elective", "open_elective"][(stage - 1) % 3]


def seed_program(writer, prefix, terms, specification):
    code, department, name, degree, intake, subjects = specification
    total = len(subjects)
    department_id = writer.save("departments", {
        "name": f"{department} ({prefix} Test Data)", "code": f"{prefix}-{code}",
        "description": "Fictional academic data for development testing.",
    })
    program_id = writer.save("programs", {
        "department_id": department_id, "name": f"{name} ({prefix})", "code": f"{prefix}-{code}",
        "degree_type": degree, "duration_years": total // 2, "total_credits": total * 12,
    })
    stages, courses = {}, {}
    for number, names in enumerate(subjects, 1):
        stages[number] = writer.save("program_semesters", {
            "program_id": program_id, "name": f"Semester {number}",
            "code": f"S{number}", "semester_number": number,
        })
        for index, course_name in enumerate(names):
            course_id = writer.save("courses", {
                "department_id": department_id, "name": course_name,
                "code": f"{prefix}-{code}{number}0{index + 1}", "credits": 4,
                "lecture_hours": 3 if index < 2 else 2, "tutorial_hours": 1,
                "practical_hours": 0 if index < 2 else 2,
            })
            course_type = subject_type(number, index, total)
            writer.save("program_courses", {
                "program_id": program_id, "course_id": course_id,
                "course_type": course_type, "is_required": course_type not in {"elective", "open_elective"},
            })
            courses[number, index] = course_id
    offerings = []
    for admission in (2025, 2026):
        version_id = writer.save("curriculum_versions", {
            "program_id": program_id, "academic_year_id": terms[admission][0],
            "name": f"{name} Regulation {admission} ({prefix})", "version": f"{prefix}-R{admission}",
            "total_semesters": total, "description": "Fictional published curriculum for development testing.",
        })
        mappings = {}
        for (number, index), course_id in courses.items():
            course_type = subject_type(number, index, total)
            mappings[number, index] = writer.save("curriculum_subjects", {
                "curriculum_version_id": version_id, "program_semester_id": stages[number],
                "course_id": course_id, "course_type": course_type,
                "is_required": course_type not in {"elective", "open_elective"},
            })
        writer.publish(version_id)
        cohort_id = writer.save("admission_cohorts", {
            "program_id": program_id, "curriculum_version_id": version_id,
            "academic_year_id": terms[admission][0], "name": f"{name} {admission}-{admission + total // 2}",
            "code": f"{prefix}-{code}-{admission}", "start_year": admission,
            "end_year": admission + total // 2, "expected_count": intake,
        })
        for number in stages:
            year_id, dated_terms = terms[admission + (number - 1) // 2]
            term_id = dated_terms[(number - 1) % 2]
            legacy = {}
            for index in range(3):
                legacy[index] = writer.save("course_offerings", {
                    "course_id": courses[number, index], "program_id": program_id,
                    "academic_year_id": year_id, "semester_id": term_id, "capacity": intake,
                })
            for section_code in ("A", "B"):
                section_id = writer.save("academic_sections", {
                    "admission_cohort_id": cohort_id, "program_semester_id": stages[number],
                    "semester_id": term_id, "name": f"{code} {admission} Semester {number} Section {section_code}",
                    "code": f"{prefix}-{code}-{admission}-S{number}-{section_code}", "capacity": intake // 2,
                })
                for index in range(3):
                    offering_id = writer.save("academic_offerings", {
                        "academic_section_id": section_id,
                        "curriculum_subject_id": mappings[number, index], "capacity": intake // 2,
                    })
                    writer.save("sections", {
                        "course_offering_id": legacy[index], "name": f"Section {section_code}",
                        "code": section_code, "capacity": intake // 2,
                    })
                    offerings.append({
                        "offering_id": offering_id, "program_id": program_id, "program_code": code,
                        "cohort_id": cohort_id, "admission_year": admission, "stage_number": number,
                        "section_id": section_id, "section_code": section_code,
                        "mapping_id": mappings[number, index], "course_id": courses[number, index],
                        "version_id": version_id, "term_id": term_id, "capacity": intake // 2,
                    })
    print(f"SEEDED {name}: {total} semesters, 2 batches, {len(offerings)} academic offerings", flush=True)
    return offerings
