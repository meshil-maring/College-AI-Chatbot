import '../../__tests__/AcademicSetup.support.ts'
import { catalogue, year } from '../../__tests__/AcademicSetup.support.ts'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { useState } from 'react'
import { beforeEach, vi } from 'vitest'
import * as api from '../../../../../services/admin/academics.ts'
import AcademicWorkspace from '../../overview/AcademicWorkspace.tsx'
import AcademicSidebar from '../../overview/AcademicSidebar.tsx'
import type { AcademicPage } from '../../overview/academicOverviewModel.ts'
import type { Semester } from '../../../../../types/academicSetup.ts'

export { auth, catalogue, year, setCatalogue } from '../../__tests__/AcademicSetup.support.ts'
export { api }
export const semester: Semester = {
  semester_id: 'semester-1',
  academic_year_id: year.academic_year_id,
  institution_id: year.institution_id,
  name: 'Semester 1',
  code: 'S1',
  semester_number: 1,
  start_date: '2026-07-01',
  end_date: '2026-12-31',
  is_active: true,
  is_current: true,
}
beforeEach(() => {
  catalogue.records.academic_years = [
    structuredClone(year),
    {
      ...year,
      academic_year_id: 'year-2',
      name: '2024 - 2025',
      code: 'AY2024',
      start_date: '2024-08-01',
      end_date: '2025-07-31',
      is_current: false,
    },
  ]
  catalogue.records.semesters = [
    structuredClone(semester),
    {
      ...semester,
      semester_id: 'semester-2',
      name: 'Semester 2',
      code: 'S2',
      semester_number: 2,
      start_date: '2027-01-01',
      end_date: '2027-06-30',
      is_current: false,
    },
  ]
  catalogue.manageable = ['academic_years', 'semesters']
  let serial = 0
  vi.mocked(api.createAcademicRecord).mockImplementation(async (_token, entity, payload) => {
    const key = entity === 'academic_years' ? 'academic_year_id' : 'semester_id'
    const record = { ...payload, [key]: `created-${++serial}`, institution_id: catalogue.institution_id }
    catalogue.records[entity]?.push(record as never)
    return record as never
  })
})

export function Workspace({ initialPage = 'calendar' }: { initialPage?: AcademicPage }) {
  const [page, setPage] = useState(initialPage)
  return (
    <>
      <AcademicSidebar page={page} onNavigate={setPage} />
      <AcademicWorkspace page={page} search="" onNavigate={setPage} onClearSearch={vi.fn()} />
    </>
  )
}
export function renderCalendar(initialPage: AcademicPage = 'calendar') {
  return render(<Workspace initialPage={initialPage} />)
}
export async function openCreate() {
  await waitFor(() => expect(screen.getByRole('button', { name: 'Add Academic Year', exact: true })).toBeEnabled())
  fireEvent.click(screen.getByRole('button', { name: 'Add Academic Year', exact: true }))
  return screen.findByRole('dialog', { name: 'Add Academic Year' })
}
export function fillYear() {
  fireEvent.change(screen.getByLabelText(/Academic Year Name/), { target: { value: ' 2028 - 2029 ' } })
  fireEvent.change(screen.getByLabelText(/Academic Year Code/), { target: { value: ' AY2028 ' } })
  fireEvent.change(screen.getByLabelText('Start Date *', { selector: '#calendar-start' }), {
    target: { value: '2028-08-01' },
  })
  fireEvent.change(screen.getByLabelText('End Date *', { selector: '#calendar-end' }), {
    target: { value: '2029-07-31' },
  })
}
