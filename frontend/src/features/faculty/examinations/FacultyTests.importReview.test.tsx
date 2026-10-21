import './__tests__/FacultyTests.support.tsx'
import { imported, open } from './__tests__/FacultyTests.support.tsx'
import { screen, waitFor, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import * as api from '../../../services/faculty/facultyTestsApi.ts'
describe('Faculty assessment workspace', () => {
  it('shows blocking import conflicts and permits revalidation', async () => {
    vi.mocked(api.uploadTestMarks).mockResolvedValue({
      ...imported,
      rows: [{ ...imported.rows[0]!, validation_status: 'CONFLICT', errors: ['Conflicting identifiers'] }],
    })
    const user = await open()
    await user.click(screen.getByRole('button', { name: 'Import' }))
    await user.upload(
      screen.getByLabelText('Choose marks spreadsheet'),
      new File(['bad'], 'marks.csv', { type: 'text/csv' }),
    )
    expect(await screen.findByText('Conflicting identifiers')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Import reviewed marks' })).toBeDisabled()
    await user.click(screen.getByRole('button', { name: 'Correct row 2' }))
    await user.click(screen.getByRole('button', { name: 'Revalidate row' }))
    await waitFor(() => expect(api.correctTestImport).toHaveBeenCalled())
    expect(screen.getByRole('button', { name: 'Import reviewed marks' })).toBeEnabled()
  })

  it('shows failed extraction without committing marks', async () => {
    vi.mocked(api.uploadTestMarks).mockRejectedValue(new Error('Malformed workbook'))
    const user = await open()
    await user.click(screen.getByRole('button', { name: 'Import' }))
    await user.upload(
      screen.getByLabelText('Choose marks spreadsheet'),
      new File(['bad'], 'marks.csv', { type: 'text/csv' }),
    )
    expect(await screen.findByRole('alert')).toHaveTextContent('Malformed workbook')
    expect(api.commitTestImport).not.toHaveBeenCalled()
  })

  it('shows correction history and uploader without rendering uploaded HTML', async () => {
    vi.mocked(api.getTestHistory).mockResolvedValue({
      imports: [imported],
      events: [
        {
          action: 'test.marks.post_lock_correct',
          actor_user_id: 'faculty-1',
          performed_at: '2026-10-07T08:00:00Z',
          record_data: { before: 75, after: 80, reason: '<script>alert(1)</script>' },
        },
      ],
    })
    const user = await open()
    await user.click(screen.getByRole('button', { name: 'History' }))
    await screen.findByText(/test.marks.post_lock_correct/)
    expect(screen.getByText(/Uploader faculty-1/)).toBeInTheDocument()
    expect(document.querySelector('script')).toBeNull()
    await user.click(screen.getByRole('button', { name: 'Review import' }))
    expect(await screen.findByText('Import completed. This review is read-only.')).toBeInTheDocument()
  })

  it('filters student search without changing identity or marks', async () => {
    const user = await open()
    await user.type(screen.getByRole('textbox', { name: 'Find student' }), 'Grace')
    const table = screen.getByRole('table', { name: 'Assessment marks roster' })
    expect(within(table).getByText('Grace Student')).toBeInTheDocument()
    expect(within(table).queryByText('Ada Student')).not.toBeInTheDocument()
  })
})
