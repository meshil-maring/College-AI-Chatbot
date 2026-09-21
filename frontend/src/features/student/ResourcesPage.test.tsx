/** Phase 6.16.3 — Learning Resources page: metadata, source types, states, safety. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { getMyNotices, getMyResources, StudentApiError } from '../../services/studentApi.ts'
import type { StudentResourceList } from '../../types/student.ts'

vi.mock('../auth/AuthProvider.tsx', () => ({
  useAuth: () => ({
    user: { email: 'student@college.edu' },
    role: 'student',
    accessToken: 'test-token',
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))
vi.mock('../../services/studentApi.ts', () => ({
  StudentApiError: class extends Error {
    status: number
    code: string | null
    constructor(status: number, message: string, _d?: unknown, code?: string | null) {
      super(message)
      this.name = 'StudentApiError'
      this.status = status
      this.code = code ?? null
    }
  },
  getMyAcademicProfile: vi.fn(),
  getMyAttendanceSummary: vi.fn(),
  getMyResultsSummary: vi.fn(),
  getMyTestResultsSummary: vi.fn(),
  getMyNotices: vi.fn(),
  getMyResources: vi.fn(),
}))

import { ResourcesPage } from './StudentPages.tsx'

const RESOURCES_FIXTURE: StudentResourceList = {
  items: [
    { resource_id: 'id-hand', title: 'Course handbook', description: 'The official handbook.', source_type: 'handbook', effective_from: '2026-09-01T00:00:00Z', effective_until: null },
    { resource_id: 'id-doc', title: 'Week 3 lecture notes', description: null, source_type: 'document', effective_from: null, effective_until: null },
  ],
  total: 2,
}

beforeEach(() => { vi.clearAllMocks() })

describe('phase 6.16.3 learning resources page', () => {
  it('renders an unknown source type gracefully instead of crashing', async () => {
    vi.mocked(getMyResources).mockResolvedValue({
      items: [
        { resource_id: 'id-mys', title: 'Mystery material', description: null, source_type: 'mystery-pack', effective_from: null, effective_until: null },
      ],
      total: 1,
    })
    render(<ResourcesPage />)
    expect(await screen.findByText('Mystery material')).toBeInTheDocument()
    expect(screen.getByText(/Mystery pack · /)).toBeInTheDocument()
  })

  it('renders a non-string source type as the em-dash fallback', async () => {
    vi.mocked(getMyResources).mockResolvedValue({
      items: [
        { resource_id: 'id-num', title: 'Numeric type', description: null, source_type: 7, effective_from: null, effective_until: null },
      ],
      total: 1,
    } as unknown as StudentResourceList)
    render(<ResourcesPage />)
    expect(await screen.findByText('Numeric type')).toBeInTheDocument()
    expect(screen.queryByText('7')).not.toBeInTheDocument()
    expect(screen.getByText(/· Effective from/)).toBeInTheDocument()
  })

  it('requests the documented page limit and nothing larger', async () => {
    vi.mocked(getMyResources).mockResolvedValue({ items: [], total: 0 })
    render(<ResourcesPage />)
    await screen.findByText('No learning resources are currently available.')
    expect(vi.mocked(getMyResources)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(getMyResources)).toHaveBeenCalledWith('test-token', 20)
  })

  it('shows a loading state while the request is in flight', () => {
    vi.mocked(getMyResources).mockReturnValue(new Promise(() => {}))
    render(<ResourcesPage />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading learning resources…')
  })

  it('shows a neutral empty state (no failure wording)', async () => {
    vi.mocked(getMyResources).mockResolvedValue({ items: [], total: 0 })
    render(<ResourcesPage />)
    expect(await screen.findByText('No learning resources are currently available.')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('recovers with retry, retrying ONLY the resources request', async () => {
    const user = userEvent.setup()
    vi.mocked(getMyResources).mockRejectedValueOnce(new StudentApiError(500, 'still broken'))
    render(<ResourcesPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load learning resources.')
    expect(screen.queryByText(/still broken/)).not.toBeInTheDocument()
    vi.mocked(getMyResources).mockResolvedValueOnce(RESOURCES_FIXTURE)
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Course handbook')).toBeInTheDocument()
    expect(vi.mocked(getMyResources)).toHaveBeenCalledTimes(2)
    expect(vi.mocked(getMyNotices)).not.toHaveBeenCalled()
  })

  it('exposes no storage internals and no open/download action', async () => {
    const leaky = {
      items: [
        {
          resource_id: 'id-leak',
          title: 'Leaky material',
          description: null,
          source_type: 'document',
          effective_from: null,
          effective_until: null,
          storage_bucket: 'internal-bucket',
          storage_object_key: 'internal/object.pdf',
          document_id: 'uuid-doc',
          institution_id: 'uuid-inst',
        },
      ],
      total: 1,
    } as unknown as StudentResourceList
    vi.mocked(getMyResources).mockResolvedValue(leaky)
    const { container } = render(<ResourcesPage />)
    await screen.findByText('Leaky material')
    const html = container.innerHTML
    expect(html).not.toContain('internal-bucket')
    expect(html).not.toContain('internal/object.pdf')
    expect(html).not.toContain('uuid-doc')
    expect(html).not.toContain('uuid-inst')
    expect(html).not.toContain('id-leak')
    // No storage-access contract exists → the page renders no link/action.
    expect(container.querySelector('a')).toBeNull()
    expect(container.querySelector('button')).toBeNull()
  })
  it('renders the page and the student-safe metadata of each resource', async () => {
    vi.mocked(getMyResources).mockResolvedValue(RESOURCES_FIXTURE)
    render(<ResourcesPage />)
    expect(screen.getByRole('heading', { name: 'Learning resources' })).toBeInTheDocument()
    expect(await screen.findByText('Course handbook')).toBeInTheDocument()
    expect(screen.getByText('The official handbook.')).toBeInTheDocument()
    expect(screen.getByText(/Handbook · Effective from/)).toBeInTheDocument()
    expect(screen.getByText(/Document · Effective from/)).toBeInTheDocument()
    expect(screen.getAllByText(/Effective from/).length).toBeGreaterThan(0)
  })
})
