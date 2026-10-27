import '../../__tests__/AcademicSetup.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, vi } from 'vitest'
import { populateStructure } from '../../__tests__/academicStructureFixtures.ts'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import AcademicSidebar from '../../overview/AcademicSidebar.tsx'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'

export { auth, catalogue, structureCatalogue } from '../../__tests__/AcademicSetup.support.ts'
export { section, cohort, stage } from '../../__tests__/academicStructureFixtures.ts'
export * as api from '../../../../../services/admin/academicStructure.ts'
export * as baseApi from '../../../../../services/admin/academics.ts'
beforeEach(populateStructure)
export function Workspace() {
  const [page, setPage] = useState<AcademicPage>('sections')
  return (
    <>
      <AcademicSidebar page={page} onNavigate={setPage} />
      <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
    </>
  )
}
export function renderSections() {
  return render(<Workspace />)
}
export async function openAdd() {
  const button = screen.getByRole('button', { name: 'Add Section', exact: true })
  await waitFor(() => expect(button).toBeEnabled())
  fireEvent.click(button)
  return within(screen.getByRole('dialog', { name: 'Add Section', exact: true }))
}
export function fillSection(name = 'Section B', code = 'CSE26B') {
  const drawer = within(screen.getByRole('dialog'))
  fireEvent.change(drawer.getByRole('textbox', { name: 'Section Name' }), { target: { value: name } })
  fireEvent.change(drawer.getByRole('textbox', { name: 'Section Code' }), { target: { value: code } })
  fireEvent.change(drawer.getByRole('combobox', { name: 'Batch' }), { target: { value: 'cohort-1' } })
  fireEvent.change(drawer.getByRole('combobox', { name: 'Program Semester' }), { target: { value: 'stage-1' } })
  fireEvent.change(drawer.getByRole('combobox', { name: 'Teaching Term' }), { target: { value: 'semester-1' } })
  return drawer
}
