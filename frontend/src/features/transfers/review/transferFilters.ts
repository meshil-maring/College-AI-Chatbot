import type { TransferInitiator, TransferRequest, TransferStatus, TransferType } from '../../../types/transfer.ts'
import { isOpenTransfer } from '../transferLabels.ts'

export type ReviewTab = 'pending' | 'history'
export type PeriodFilter = 'any' | '7' | '30' | '90'
export type SortOrder = 'newest' | 'oldest'

export interface TransferFilters {
  search: string
  status: TransferStatus | 'all'
  type: TransferType | 'all'
  initiatedBy: TransferInitiator | 'all'
  programId: string
  departmentId: string
  period: PeriodFilter
  sort: SortOrder
}

export const EMPTY_FILTERS: TransferFilters = {
  search: '',
  status: 'all',
  type: 'all',
  initiatedBy: 'all',
  programId: '',
  departmentId: '',
  period: 'any',
  sort: 'newest',
}

export const TAB_STATUSES: Record<ReviewTab, TransferStatus[]> = {
  pending: ['submitted', 'under_review'],
  history: ['approved', 'rejected', 'cancelled'],
}

export function tabFor(status: TransferStatus): ReviewTab {
  return isOpenTransfer(status) ? 'pending' : 'history'
}

/** The date a request is listed by: pending by submission, history by its outcome. */
export function activityDate(request: TransferRequest) {
  return request.decided_at ?? request.cancelled_at ?? request.submitted_at
}

export function hasActiveFilters(filters: TransferFilters) {
  return (Object.keys(EMPTY_FILTERS) as (keyof TransferFilters)[]).some(
    (key) => key !== 'sort' && filters[key] !== EMPTY_FILTERS[key],
  )
}

function searchText(request: TransferRequest) {
  const sections = [request.from_section, request.to_section].flatMap((section) =>
    section
      ? [
          section.program_name,
          section.program_code,
          section.section_name,
          section.section_code,
          section.department_name,
        ]
      : [],
  )
  return [request.student_name, request.register_number, request.reason, request.decision_comment, ...sections]
    .filter(Boolean)
    .join(' ')
    .toLocaleLowerCase()
}

export function filterTransfers(
  requests: TransferRequest[],
  tab: ReviewTab,
  filters: TransferFilters,
  now: number = Date.now(),
) {
  const terms = filters.search.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  const since = filters.period === 'any' ? null : now - Number(filters.period) * 86_400_000
  const touches = (request: TransferRequest, pick: (section: NonNullable<TransferRequest['to_section']>) => string) =>
    [request.from_section, request.to_section].some((section) => section && pick(section))
  const matches = requests.filter((request) => {
    if (!TAB_STATUSES[tab].includes(request.status)) return false
    if (filters.status !== 'all' && request.status !== filters.status) return false
    if (filters.type !== 'all' && request.transfer_type !== filters.type) return false
    if (filters.initiatedBy !== 'all' && (request.initiated_by ?? 'student') !== filters.initiatedBy) return false
    if (filters.programId && !touches(request, (section) => (section.program_id === filters.programId ? 'y' : '')))
      return false
    if (
      filters.departmentId &&
      !touches(request, (section) => (section.department_id === filters.departmentId ? 'y' : ''))
    )
      return false
    if (since !== null && new Date(activityDate(request)).getTime() < since) return false
    if (terms.length) {
      const text = searchText(request)
      if (!terms.every((term) => text.includes(term))) return false
    }
    return true
  })
  const direction = filters.sort === 'newest' ? -1 : 1
  return matches.sort((a, b) => direction * (new Date(activityDate(a)).getTime() - new Date(activityDate(b)).getTime()))
}

export function statusCounts(requests: TransferRequest[]) {
  const counts: Record<TransferStatus, number> = {
    submitted: 0,
    under_review: 0,
    approved: 0,
    rejected: 0,
    cancelled: 0,
  }
  for (const request of requests) counts[request.status] += 1
  return counts
}

/** Programs and departments that appear on either side of any request, for filter menus. */
export function filterFacets(requests: TransferRequest[]) {
  const programs = new Map<string, string>()
  const departments = new Map<string, string>()
  for (const request of requests) {
    for (const section of [request.from_section, request.to_section]) {
      if (!section) continue
      programs.set(section.program_id, section.program_name)
      departments.set(section.department_id, section.department_name)
    }
  }
  const sorted = (map: Map<string, string>) =>
    [...map].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name))
  return { programs: sorted(programs), departments: sorted(departments) }
}
