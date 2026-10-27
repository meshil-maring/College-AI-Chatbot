import { api, catalogue, year, fillYear, openCreate, renderCalendar } from './Calendar.support.tsx'
import { act, fireEvent, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AdminApiError } from '../../../../../services/admin/http.ts'
import type { AcademicYear } from '../../../../../types/academicSetup.ts'

describe('Calendar save recovery', () => {
  it('retries only the remaining semesters after a partial save', async () => {
    const original = vi.mocked(api.createAcademicRecord).getMockImplementation()!
    let requests = 0
    vi.mocked(api.createAcademicRecord).mockImplementation(async (token, entity, payload) => {
      if (++requests === 3) throw new Error('Semester service unavailable.')
      return original(token, entity, payload)
    })
    renderCalendar()
    await openCreate()
    fillYear()
    fireEvent.click(screen.getByRole('button', { name: 'Create Academic Year' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Semester service unavailable.')
    expect(screen.getByText(/1 of 2 semesters saved/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Academic Year Name/)).toBeDisabled()
    expect(
      within(screen.getByRole('group', { name: /Semester 1 · Saved/ })).getByLabelText('Start Date'),
    ).toBeDisabled()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Retry Remaining Semesters' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: 'Retry Remaining Semesters' }))
    await screen.findByText('Academic year created successfully.')
    expect(vi.mocked(api.createAcademicRecord).mock.calls.filter((call) => call[1] === 'academic_years')).toHaveLength(
      1,
    )
    expect(catalogue.records.semesters!.filter((item) => item.academic_year_id === 'created-1')).toHaveLength(2)
  })

  it('retains entries after a duplicate response and allows correction', async () => {
    vi.mocked(api.createAcademicRecord).mockRejectedValueOnce(
      new AdminApiError(409, 'An academic year with this code already exists.', undefined, 'ACADEMIC_DUPLICATE'),
    )
    renderCalendar()
    await openCreate()
    fillYear()
    fireEvent.click(screen.getByRole('button', { name: 'Create Academic Year' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('already exists')
    expect(screen.getByLabelText(/Academic Year Code/)).toHaveValue(' AY2028 ')
    fireEvent.change(screen.getByLabelText(/Academic Year Code/), { target: { value: 'AY2028B' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Academic Year' }))
    await screen.findByText('Academic year created successfully.')
  })

  it('blocks duplicate submissions and disables edits during a save', async () => {
    let reject!: (cause: Error) => void
    vi.mocked(api.createAcademicRecord).mockImplementationOnce(
      () =>
        new Promise<AcademicYear>((_done, fail) => {
          reject = fail
        }) as never,
    )
    renderCalendar()
    await openCreate()
    fillYear()
    const button = screen.getByRole('button', { name: 'Create Academic Year' })
    fireEvent.click(button)
    fireEvent.click(button)
    expect(api.createAcademicRecord).toHaveBeenCalledTimes(1)
    expect(screen.getByLabelText(/Academic Year Name/)).toBeDisabled()
    await act(async () => reject(new Error('Offline')))
    expect(await screen.findByRole('alert')).toHaveTextContent('Offline')
    expect(screen.getByLabelText(/Academic Year Name/)).toHaveValue(' 2028 - 2029 ')
    expect(screen.getByRole('button', { name: 'Create Academic Year' })).toBeEnabled()
    expect(catalogue.records.academic_years).toHaveLength(2)
    expect(catalogue.records.academic_years![0].academic_year_id).toBe(year.academic_year_id)
  })
})
