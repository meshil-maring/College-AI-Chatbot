import './__tests__/ResultsDetail.support.tsx'
import { render, screen, within } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { getMyResultsSummary, getMyTestResultsSummary } from '../../../services/students/studentApi.ts'
import type { StudentOwnResults } from '../../../types/student.ts'
import { ResultsDetailPage } from './ResultsDetail.tsx'
describe('results detail record integrity', () => {
  it('falls back to the course code when no course name is provided', async () => {
    vi.mocked(getMyTestResultsSummary).mockResolvedValue({
      summary: { records_available: true, total_results: 1 },
      records: [
        {
          test_name: 'Quiz 2',
          test_type: 'internal',
          course_code: 'CS302',
          course_name: null,
          max_marks: 20,
          scored_marks: 18,
          percentage: 90,
          letter_grade: 'A+',
          conducted_at: '2026-08-02',
        },
      ],
    })
    render(<ResultsDetailPage />)
    const tests = await screen.findByRole('table', { name: 'Your published test scores' })
    expect(within(tests).getByText('CS302')).toBeInTheDocument()
    expect(within(tests).getByText('18/20')).toBeInTheDocument()
  })

  it('renders only student-safe fields (no internal identifiers)', async () => {
    vi.mocked(getMyResultsSummary).mockResolvedValue({
      summary: { records_available: true, total_results: 1 },
      records: [
        {
          result_type: 'semester',
          total_credits_earned: 20,
          total_credits_max: 22,
          sgpa: 8.5,
          cgpa: 8.2,
          status: 'pass',
          issued_at: '2026-08-01',
          result_id: 'res-11111111',
          student_id: 'stu-22222222',
          institution_id: 'inst-33333333',
        },
      ],
    } as unknown as StudentOwnResults)
    render(<ResultsDetailPage />)
    expect(await screen.findByText('Semester')).toBeInTheDocument()
    expect(screen.queryByText(/11111111|22222222|33333333/)).toBeNull()
  })

  it('keeps wide tables scrollable and the summary grid responsive', async () => {
    const { container } = render(<ResultsDetailPage />)
    const academic = await screen.findByRole('table', { name: 'Your published examination results' })
    expect(academic.parentElement?.className).toContain('overflow-x-auto')
    expect(academic.className).toContain('min-w-')
    const summary = screen.getByText('Latest SGPA').closest('dl')
    expect(summary?.className).toContain('grid-cols-2')
    expect(summary?.className).toContain('sm:grid-cols-4')
    expect(container.firstElementChild?.className).toContain('overflow-x-clip')
  })
})
