import '../../__tests__/AcademicSetup.support.ts'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { vi } from 'vitest'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import AcademicSidebar from '../../overview/AcademicSidebar.tsx'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'

export { auth, catalogue, department, program, setCatalogue } from '../../__tests__/AcademicSetup.support.ts'
export * as api from '../../../../../services/admin/academics.ts'

export function Workspace({ initialPage = 'departments' }: { initialPage?: AcademicPage }) {
  const [page, setPage] = useState(initialPage)
  return (
    <>
      <AcademicSidebar page={page} onNavigate={setPage} />
      <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
    </>
  )
}
export function renderDepartments(initialPage: AcademicPage = 'departments') {
  return render(<Workspace initialPage={initialPage} />)
}
export async function openCreate() {
  await waitFor(() => expect(screen.getAllByRole('button', { name: 'Add Department', exact: true })[0]).toBeEnabled())
  fireEvent.click(screen.getAllByRole('button', { name: 'Add Department', exact: true })[0])
  await screen.findByRole('dialog', { name: 'Add Department' })
}
export function fillDepartment(name = 'Applied Sciences', code = ' AS ') {
  fireEvent.change(screen.getByRole('textbox', { name: /Department Name/ }), { target: { value: name } })
  fireEvent.change(screen.getByRole('textbox', { name: /Department Code/ }), { target: { value: code } })
  fireEvent.click(screen.getByRole('radio', { name: /^Active/ }))
}
