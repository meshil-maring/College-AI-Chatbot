import '../../__tests__/AcademicSetup.support.ts'
import { catalogue, structureCatalogue } from '../../__tests__/AcademicSetup.support.ts'
import { course, semester } from '../../__tests__/academicExportFixtures.ts'
import { mapping, stage } from '../../__tests__/academicStructureFixtures.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, vi } from 'vitest'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import AcademicSidebar from '../../overview/AcademicSidebar.tsx'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'

export { auth, catalogue, department, setCatalogue, structureCatalogue } from '../../__tests__/AcademicSetup.support.ts'
export { course as subject, semester } from '../../__tests__/academicExportFixtures.ts'
export { mapping, stage } from '../../__tests__/academicStructureFixtures.ts'
export * as api from '../../../../../services/admin/academics.ts'

beforeEach(() => {
  catalogue.records.courses = [structuredClone(course)]
  catalogue.records.semesters = [structuredClone(semester)]
  structureCatalogue.records.program_semesters = [structuredClone(stage)]
  structureCatalogue.records.curriculum_subjects = [structuredClone(mapping)]
  catalogue.manageable.push('courses')
})

export function Workspace({ initialPage = 'subjects' }: { initialPage?: AcademicPage }) {
  const [page, setPage] = useState(initialPage)
  return (
    <>
      <AcademicSidebar page={page} onNavigate={setPage} />
      <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
    </>
  )
}
export function renderSubjects(initialPage: AcademicPage = 'subjects') {
  return render(<Workspace initialPage={initialPage} />)
}
export async function openCreate() {
  await waitFor(() => expect(screen.getAllByRole('button', { name: 'Add Subject', exact: true })[0]).toBeEnabled(), {
    timeout: 5000,
  })
  fireEvent.click(screen.getAllByRole('button', { name: 'Add Subject', exact: true })[0])
  await screen.findByRole('dialog', { name: 'Add Subject' })
}
export function fillSubject() {
  fireEvent.change(screen.getByRole('textbox', { name: /Subject Name/ }), {
    target: { value: ' Applied Mathematics ' },
  })
  fireEvent.change(screen.getByRole('textbox', { name: /Subject Code/ }), { target: { value: ' AM ' } })
  const form = within(screen.getByRole('form', { name: 'New subject' }))
  fireEvent.change(form.getByRole('combobox', { name: /^Department/ }), { target: { value: 'department-1' } })
}
