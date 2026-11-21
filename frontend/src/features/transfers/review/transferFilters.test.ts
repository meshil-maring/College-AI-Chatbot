import { describe, expect, it } from 'vitest'
import { requestFixture, sectionFixture } from '../__tests__/transferFixture.ts'
import { EMPTY_FILTERS, filterFacets, filterTransfers, hasActiveFilters, statusCounts } from './transferFilters.ts'

const NOW = new Date('2026-11-21T00:00:00Z').getTime()
const requests = [
  requestFixture({ transfer_request_id: 'open-old', submitted_at: '2026-08-01T00:00:00Z' }),
  requestFixture({ transfer_request_id: 'open-new', status: 'under_review', submitted_at: '2026-11-19T00:00:00Z' }),
  requestFixture({
    transfer_request_id: 'done',
    status: 'approved',
    transfer_type: 'program_transfer',
    initiated_by: 'hod',
    decided_at: '2026-11-20T00:00:00Z',
    to_section: sectionFixture({ program_id: 'program-ece', program_name: 'B.Tech ECE', department_id: 'dep-ec' }),
  }),
]

describe('transfer review filters', () => {
  it('splits pending and history and sorts by activity date', () => {
    expect(filterTransfers(requests, 'pending', EMPTY_FILTERS, NOW).map((r) => r.transfer_request_id)).toEqual([
      'open-new',
      'open-old',
    ])
    expect(
      filterTransfers(requests, 'pending', { ...EMPTY_FILTERS, sort: 'oldest' }, NOW).map((r) => r.transfer_request_id),
    ).toEqual(['open-old', 'open-new'])
    expect(filterTransfers(requests, 'history', EMPTY_FILTERS, NOW).map((r) => r.transfer_request_id)).toEqual(['done'])
  })
  it('combines status, type, initiator, program, department, period and search', () => {
    const ids = (filters: Partial<typeof EMPTY_FILTERS>, tab: 'pending' | 'history' = 'pending') =>
      filterTransfers(requests, tab, { ...EMPTY_FILTERS, ...filters }, NOW).map((r) => r.transfer_request_id)
    expect(ids({ status: 'under_review' })).toEqual(['open-new'])
    expect(ids({ period: '30' })).toEqual(['open-new'])
    expect(ids({ type: 'program_transfer' }, 'history')).toEqual(['done'])
    expect(ids({ initiatedBy: 'student' }, 'history')).toEqual([])
    expect(ids({ programId: 'program-ece' }, 'history')).toEqual(['done'])
    expect(ids({ departmentId: 'dep-ec' })).toEqual([])
    expect(ids({ search: 'asha  ece' }, 'history')).toEqual(['done'])
    expect(ids({ search: 'timetable' })).toHaveLength(2)
  })
  it('counts statuses, lists facets and detects active filters', () => {
    expect(statusCounts(requests)).toMatchObject({ submitted: 1, under_review: 1, approved: 1 })
    expect(filterFacets(requests).programs.map((p) => p.name)).toEqual(['B.Tech CSE', 'B.Tech ECE'])
    expect(hasActiveFilters(EMPTY_FILTERS)).toBe(false)
    expect(hasActiveFilters({ ...EMPTY_FILTERS, sort: 'oldest' })).toBe(false)
    expect(hasActiveFilters({ ...EMPTY_FILTERS, search: 'x' })).toBe(true)
  })
})
