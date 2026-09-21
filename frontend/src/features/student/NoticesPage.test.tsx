/** Phase 6.16.3 — Notices page: presentation, ordering, limits, states, safety. */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { getMyNotices, getMyResources, StudentApiError } from '../../services/studentApi.ts'
import type { StudentNoticeList } from '../../types/student.ts'

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

import { NoticesPage } from './StudentPages.tsx'

/** Exactly what the backend sends, in the backend's order (pinned, then newest). */
const SERVER_ORDER: StudentNoticeList = {
  items: [
    { notice_id: 'id-pin', title: 'Pinned maintenance', content: 'Water outage on Monday.', category: 'facilities', priority: 'high', is_pinned: true, published_at: '2026-09-01T00:00:00Z', expires_at: null },
    { notice_id: 'id-new', title: 'Newer notice', content: 'Exams begin Friday.', category: 'exam', priority: 'normal', is_pinned: false, published_at: '2026-09-05T00:00:00Z', expires_at: null },
    { notice_id: 'id-old', title: 'Older notice', content: 'Library hours changed.', category: 'general', priority: 'normal', is_pinned: false, published_at: '2026-09-03T00:00:00Z', expires_at: null },
  ],
  total: 3,
}

beforeEach(() => { vi.clearAllMocks() })

describe('phase 6.16.3 notices page', () => {
  it('renders the page and every student-facing notice field', async () => {
    vi.mocked(getMyNotices).mockResolvedValue(SERVER_ORDER)
    render(<NoticesPage />)
    expect(screen.getByRole('heading', { name: 'Notices from your institution' })).toBeInTheDocument()
    expect(await screen.findByText('Pinned maintenance')).toBeInTheDocument()
    expect(screen.getByText('Water outage on Monday.')).toBeInTheDocument()
    expect(screen.getByText('Pinned')).toBeInTheDocument()
    expect(screen.getByText(/Facilities · High ·/)).toBeInTheDocument()
    const firstItem = screen.getAllByRole('listitem')[0]
    expect(firstItem.textContent).toContain('2026')
  })

  it('preserves the backend ordering (pinned first, then newest)', async () => {
    vi.mocked(getMyNotices).mockResolvedValue(SERVER_ORDER)
    const { container } = render(<NoticesPage />)
    await screen.findByText('Pinned maintenance')
    const titles = Array.from(container.querySelectorAll('li')).map((li) => li.textContent ?? '')
    expect(titles).toHaveLength(3)
    expect(titles[0]).toContain('Pinned maintenance')
    expect(titles[1]).toContain('Newer notice')
    expect(titles[2]).toContain('Older notice')
  })

  it('requests the documented page limit and nothing larger', async () => {
    vi.mocked(getMyNotices).mockResolvedValue({ items: [], total: 0 })
    render(<NoticesPage />)
    await screen.findByText('No recent notices.')
    expect(vi.mocked(getMyNotices)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(getMyNotices)).toHaveBeenCalledWith('test-token', 20)
  })
  it('shows a loading state while the request is in flight', () => {
    vi.mocked(getMyNotices).mockReturnValue(new Promise(() => {}))
    render(<NoticesPage />)
    expect(screen.getByRole('status')).toHaveTextContent('Loading notices…')
    expect(screen.queryByText('No recent notices.')).not.toBeInTheDocument()
  })

  it('shows a neutral empty state (no failure wording)', async () => {
    vi.mocked(getMyNotices).mockResolvedValue({ items: [], total: 0 })
    render(<NoticesPage />)
    expect(await screen.findByText('No recent notices.')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('recovers with retry, retrying ONLY the notices request', async () => {
    const user = userEvent.setup()
    vi.mocked(getMyNotices).mockRejectedValueOnce(new StudentApiError(500, 'server exploded'))
    render(<NoticesPage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load notices.')
    expect(screen.queryByText(/server exploded/)).not.toBeInTheDocument()
    vi.mocked(getMyNotices).mockResolvedValueOnce(SERVER_ORDER)
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Pinned maintenance')).toBeInTheDocument()
    expect(vi.mocked(getMyNotices)).toHaveBeenCalledTimes(2)
    expect(vi.mocked(getMyResources)).not.toHaveBeenCalled()
  })

  it('renders notice text safely: no HTML execution, no internal identifiers', async () => {
    const leaky = {
      items: [
        {
          notice_id: 'id-x',
          title: '<img src=x onerror=alert(1)>',
          content: '<script>alert(1)</script>',
          category: 'general',
          priority: 'normal',
          is_pinned: false,
          published_at: null,
          expires_at: null,
          institution_id: 'uuid-inst',
          created_by: 'uuid-creator',
        },
      ],
      total: 1,
    } as unknown as StudentNoticeList
    vi.mocked(getMyNotices).mockResolvedValue(leaky)
    const { container } = render(<NoticesPage />)
    await screen.findByText(/<script>alert\(1\)<\/script>/)
    expect(container.querySelector('script')).toBeNull()
    expect(container.querySelector('img')).toBeNull()
    const html = container.innerHTML
    expect(html).not.toContain('uuid-inst')
    expect(html).not.toContain('uuid-creator')
    expect(html).not.toContain('id-x')
  })

  it('renders a malformed/unknown category or priority without crashing', async () => {
    const weird = {
      items: [
        { notice_id: 'id-y', title: 'Odd notice', content: 'Body', category: 42, priority: null, is_pinned: false, published_at: null, expires_at: null },
      ],
      total: 1,
    } as unknown as StudentNoticeList
    vi.mocked(getMyNotices).mockResolvedValue(weird)
    render(<NoticesPage />)
    expect(await screen.findByText('Odd notice')).toBeInTheDocument()
    expect(screen.queryByText('42')).not.toBeInTheDocument()
    expect(screen.getByText(/· .* ·/)).toBeInTheDocument()
  })
})
