import '../../__tests__/AcademicSetup.support.ts'
import { auth, catalogue } from '../../__tests__/AcademicSetup.support.ts'
import { course, link, semester, populateExportCatalogue } from '../../__tests__/academicExportFixtures.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, vi } from 'vitest'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import { ExistingCurriculumMappings } from '../ExistingCurriculumMappings.tsx'
import { hasAcademicCatalogueReadAccess } from '../../overview/useAcademicOverview.ts'
import AcademicSidebar from '../../overview/AcademicSidebar.tsx'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'

export { auth, catalogue, department, program, year, setCatalogue } from '../../__tests__/AcademicSetup.support.ts'
export { course, link, semester } from '../../__tests__/academicExportFixtures.ts'
export * as api from '../../../../../services/admin/academics.ts'
export const extraCourse = { ...course, course_id: 'course-2', code: 'CS502', name: 'Computer Vision', credits: 4 }

beforeEach(() => {
  populateExportCatalogue()
  catalogue.records.courses!.push(structuredClone(extraCourse))
  catalogue.records.program_courses = [{ ...link, semester_id: semester.semester_id }]
})
export function Workspace({ initialPage = 'curriculum' }: { initialPage?: AcademicPage }) {
  const [page, setPage] = useState(initialPage)
  return (
    <>
      <AcademicSidebar page={page} onNavigate={setPage} />
      {['curriculum', 'curriculum-versions', 'curriculum-subjects'].includes(page) ? (
        <ExistingCurriculumMappings
          key={JSON.stringify([auth.accessToken, auth.user.institution_id, auth.user.effective_permissions])}
          accessToken={auth.accessToken!}
          identity={JSON.stringify([auth.accessToken, auth.user.institution_id])}
          institutionId={auth.user.institution_id}
          canReadCatalogues={hasAcademicCatalogueReadAccess(auth.user.effective_permissions)}
          initialTab={page === 'curriculum-subjects' ? 'mapping' : 'list'}
          onOverview={() => setPage('overview')}
        />
      ) : (
        <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
      )}
    </>
  )
}
export function renderCurriculum(initialPage: AcademicPage = 'curriculum') {
  return render(<Workspace initialPage={initialPage} />)
}
export async function loaded() {
  await waitFor(
    () => expect(screen.getByRole('region', { name: 'Curriculum summary' })).toHaveAttribute('aria-busy', 'false'),
    { timeout: 5000 },
  )
}
export async function openMapping() {
  await loaded()
  fireEvent.click(screen.getByRole('button', { name: 'Add Subject', exact: true }))
  return within(await screen.findByRole('dialog', { name: 'Add Subject' }))
}
export function chooseSubject() {
  fireEvent.change(screen.getByRole('combobox', { name: 'Subject', exact: true }), {
    target: { value: extraCourse.course_id },
  })
}
