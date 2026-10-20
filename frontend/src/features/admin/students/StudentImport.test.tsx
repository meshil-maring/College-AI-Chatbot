import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import StudentImport from './StudentImport.tsx'
import * as files from './studentImport.ts'
import type { ImportStudent } from './studentImport.ts'

vi.mock('./studentImport.ts', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./studentImport.ts')>()),
  readStudentFile: vi.fn(),
  downloadCsv: vi.fn(),
}))
const rows = (): ImportStudent[] =>
  Array.from({ length: 10 }, (_, index) => ({
    row: index + 2,
    name: `Student ${index}`,
    registerNumber: `REG${index}`,
    rollNumber: `ROLL${index}`,
    email: `student${index}@example.test`,
    attendance: '90',
  }))

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(files.readStudentFile).mockResolvedValue(rows())
})
async function upload() {
  fireEvent.change(screen.getByLabelText('Choose student file'), {
    target: {
      files: [new File(['test'], 'students.csv', { type: 'text/csv' })],
    },
  })
  await screen.findByText('students.csv')
}

describe('student import review interactions', () => {
  it('starts without fabricated records and shows the upload format', () => {
    render(<StudentImport students={[]} directoryReady onBack={vi.fn()} />)
    expect(screen.getByRole('button', { name: 'Choose File' })).toBeEnabled()
    expect(
      screen.getByText(
        'Validate the uploaded file and review student records before importing.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByText('STUDENT MANAGEMENT')).not.toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.getByText(/1,000 records/)).toBeInTheDocument()
  })
  it('paginates, searches, selects only valid rows and reviews the selected count', async () => {
    render(<StudentImport students={[]} directoryReady onBack={vi.fn()} />)
    await upload()
    expect(screen.getByText('Showing 1–8 of 10 records')).toBeInTheDocument()
    expect(screen.getByText('Ready to import')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }))
    expect(screen.getByText('Showing 9–10 of 10 records')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Select Student 8' }))
    fireEvent.change(
      screen.getByRole('searchbox', { name: 'Search import records' }),
      { target: { value: 'REG0' } },
    )
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(
      2,
    )
    fireEvent.click(screen.getByRole('button', { name: 'Continue to Import' }))
    expect(
      screen.getByRole('heading', { name: '9 records selected for import' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Import unavailable' }),
    ).toBeDisabled()
    expect(
      screen.getByText(/No student records have been created or changed/),
    ).toBeInTheDocument()
  })
  it('excludes invalid rows from selection and downloads the entire report despite filters', async () => {
    vi.mocked(files.readStudentFile).mockResolvedValue([
      rows()[0],
      { ...rows()[1], rollNumber: '' },
    ])
    render(<StudentImport students={[]} directoryReady onBack={vi.fn()} />)
    await upload()
    expect(
      screen.getByRole('checkbox', { name: 'Select Student 1' }),
    ).toBeDisabled()
    fireEvent.click(
      within(
        screen.getByRole('group', { name: 'Validation status' }),
      ).getByRole('button', { name: 'Invalid (1)' }),
    )
    expect(
      screen.queryByRole('checkbox', { name: 'Select Student 0' }),
    ).not.toBeInTheDocument()
    fireEvent.click(
      screen.getByRole('button', { name: 'Download Validation Report' }),
    )
    expect(files.downloadCsv).toHaveBeenCalledWith(
      'student-validation-report.csv',
      expect.arrayContaining([
        expect.arrayContaining(['Student 0']),
        expect.arrayContaining(['Student 1']),
      ]),
    )
  })
  it('offers full and problem-only reports from the split download control', async () => {
    vi.mocked(files.readStudentFile).mockResolvedValue([
      rows()[0],
      { ...rows()[1], rollNumber: '' },
    ])
    render(<StudentImport students={[]} directoryReady onBack={vi.fn()} />)
    await upload()
    fireEvent.click(
      screen.getByRole('button', { name: 'More download options' }),
    )
    fireEvent.click(
      screen.getByRole('menuitem', { name: 'Problems only (.csv)' }),
    )
    expect(files.downloadCsv).toHaveBeenCalledTimes(1)
    const [reportName, reportRows] = vi.mocked(files.downloadCsv).mock.calls[0]
    expect(reportName).toBe('student-validation-report.csv')
    expect(reportRows).toHaveLength(2)
    expect(reportRows[1]).toContain('Student 1')
    expect(reportRows.flat()).not.toContain('Student 0')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
  })
  it('blocks continuation until directory checks succeed and surfaces unreadable files', async () => {
    const view = render(
      <StudentImport students={[]} directoryReady={false} onBack={vi.fn()} />,
    )
    await upload()
    expect(
      screen.getByRole('button', { name: 'Continue to Import' }),
    ).toBeDisabled()
    view.rerender(
      <StudentImport students={[]} directoryReady onBack={vi.fn()} />,
    )
    expect(
      screen.getByRole('button', { name: 'Continue to Import' }),
    ).toBeEnabled()
    vi.mocked(files.readStudentFile).mockRejectedValue(
      new Error('Missing columns: email'),
    )
    fireEvent.change(screen.getByLabelText('Choose student file'), {
      target: { files: [new File([], 'bad.csv')] },
    })
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Missing columns: email',
      ),
    )
    expect(screen.getByText('students.csv')).toBeInTheDocument()
  })
})
