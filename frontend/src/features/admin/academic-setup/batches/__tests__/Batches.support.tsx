import '../../__tests__/AcademicSetup.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, vi } from 'vitest'
import { populateStructure } from '../../__tests__/academicStructureFixtures.ts'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import AcademicSidebar from '../../overview/AcademicSidebar.tsx'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'

export { auth, catalogue, structureCatalogue, program, year } from '../../__tests__/AcademicSetup.support.ts'
export { cohort, version } from '../../__tests__/academicStructureFixtures.ts'
export * as api from '../../../../../services/admin/academicStructure.ts'
export * as baseApi from '../../../../../services/admin/academics.ts'
beforeEach(populateStructure)

export function Workspace() {
  const [page, setPage] = useState<AcademicPage>('cohorts')
  return (
    <>
      <AcademicSidebar page={page} onNavigate={setPage} />
      <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
    </>
  )
}
export function renderBatches() {
  return render(<Workspace />)
}
export async function openAdd() {
  const button = await screen.findByRole('button', { name: 'Add Batch', exact: true })
  await waitFor(() => expect(button).toBeEnabled())
  fireEvent.click(button)
  return within(screen.getByRole('dialog', { name: 'Add Batch' }))
}
export function fillBatch(name = 'CSE Summer', code = 'CSE-SUM') {
  const drawer = within(screen.getByRole('dialog'))
  fireEvent.change(drawer.getByRole('textbox', { name: 'Batch Name' }), { target: { value: name } })
  fireEvent.change(drawer.getByRole('textbox', { name: 'Batch Code' }), { target: { value: code } })
  fireEvent.change(drawer.getByRole('combobox', { name: 'Program' }), { target: { value: 'program-1' } })
  fireEvent.change(drawer.getByRole('combobox', { name: 'Curriculum Version' }), { target: { value: 'version-1' } })
  fireEvent.change(drawer.getByRole('combobox', { name: 'Academic Year' }), { target: { value: 'year-1' } })
  return drawer
}
