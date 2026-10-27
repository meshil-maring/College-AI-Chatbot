import '../../__tests__/AcademicSetup.support.ts'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { useState } from 'react'
import { vi } from 'vitest'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import AcademicSidebar from '../../overview/AcademicSidebar.tsx'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'

export { auth, catalogue, department, program, setCatalogue } from '../../__tests__/AcademicSetup.support.ts'
export * as api from '../../../../../services/admin/academics.ts'

export function Workspace({ initialPage = 'programs' }: { initialPage?: AcademicPage }) {
  const [page, setPage] = useState(initialPage)
  return (
    <>
      <AcademicSidebar page={page} onNavigate={setPage} />
      <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
    </>
  )
}
export function renderPrograms(initialPage: AcademicPage = 'programs') {
  return render(<Workspace initialPage={initialPage} />)
}
export async function openCreate() {
  await waitFor(() => expect(screen.getAllByRole('button', { name: 'Add Program', exact: true })[0]).toBeEnabled(), {
    timeout: 5000,
  })
  fireEvent.click(screen.getAllByRole('button', { name: 'Add Program', exact: true })[0])
  await screen.findByRole('dialog', { name: 'Add Program' })
}
export function fillProgram() {
  fireEvent.change(screen.getByRole('textbox', { name: /Program Name/ }), {
    target: { value: ' Applied Mathematics ' },
  })
  fireEvent.change(screen.getByRole('textbox', { name: /Program Code/ }), { target: { value: ' AM ' } })
  const form = within(screen.getByRole('form', { name: 'New degree program' }))
  fireEvent.change(form.getByRole('combobox', { name: /^Department/ }), { target: { value: 'department-1' } })
  fireEvent.change(form.getByRole('combobox', { name: /Degree Type/ }), { target: { value: 'B.Sc' } })
  fireEvent.change(screen.getByRole('spinbutton', { name: /Duration/ }), { target: { value: '3.5' } })
}
