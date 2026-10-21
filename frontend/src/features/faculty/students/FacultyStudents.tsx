import { navigateTo } from '../../../lib/navigation.ts'
import { facultyStudentsPath } from '../workspace/facultyRoutes.ts'
import { StudentWorkspace } from './StudentWorkspace.tsx'
import { useFacultyStudentSections } from './useFacultyStudentSections.ts'

export default function FacultyStudents(props: { accessToken: string; scopeVersion?: string }) {
  return <FacultyStudentsWorkspace key={JSON.stringify([props.accessToken, props.scopeVersion])} {...props} />
}

function FacultyStudentsWorkspace({ accessToken, scopeVersion = '' }: { accessToken: string; scopeVersion?: string }) {
  const scope = useFacultyStudentSections(accessToken, scopeVersion)
  return (
    <StudentWorkspace
      {...scope}
      accessToken={accessToken}
      onNavigate={(page, id, replace) => navigateTo(facultyStudentsPath(id, page), { replace })}
    />
  )
}

export { StudentWorkspace } from './StudentWorkspace.tsx'
