import { navigateTo } from '../../../lib/navigation.ts'
import { facultyStudentsPath } from '../workspace/facultyRoutes.ts'
import { useFacultyStudentSections } from './useFacultyStudentSections.ts'
import { StudentsNavigation } from '../../students/StudentsUI.tsx'
import { STUDENT_PAGES } from '../../students/studentsNavigation.ts'

export default function FacultyStudentsNavigation({
  accessToken,
  scopeVersion,
  onNavigate,
}: {
  accessToken: string
  scopeVersion?: string
  onNavigate?: () => void
}) {
  const { page, sectionId, selected } = useFacultyStudentSections(accessToken, scopeVersion)
  const items = STUDENT_PAGES.map(({ key, label }) => ({
    key,
    label,
    href: facultyStudentsPath(selected?.section_id ?? (sectionId || undefined), key),
    disabled: (key === 'register' || key === 'subject-assignment') && !selected?.can_manage,
    title:
      key === 'register' || key === 'subject-assignment'
        ? 'This action requires permission to manage this section'
        : undefined,
  }))
  return (
    <StudentsNavigation
      id="faculty-students-pages"
      active={page}
      items={items}
      onNavigate={(target) => {
        navigateTo(facultyStudentsPath(selected?.section_id ?? (sectionId || undefined), target))
        onNavigate?.()
      }}
    />
  )
}
