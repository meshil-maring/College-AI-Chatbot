import type {
  TransferEventAction,
  TransferInitiator,
  TransferSection,
  TransferStatus,
  TransferType,
} from '../../types/transfer.ts'

export const TRANSFER_STATUS_LABEL: Record<TransferStatus, string> = {
  submitted: 'Submitted',
  under_review: 'Under review',
  approved: 'Approved',
  rejected: 'Rejected',
  cancelled: 'Cancelled',
}

export const TRANSFER_STATUS_TONE: Record<TransferStatus, string> = {
  submitted: 'bg-info-bg text-info',
  under_review: 'bg-warning-bg text-warning',
  approved: 'bg-success-bg text-success',
  rejected: 'bg-danger-bg text-danger',
  cancelled: 'bg-neutral-bg text-neutral',
}

export const TRANSFER_TYPE_LABEL: Record<TransferType, string> = {
  section_transfer: 'Section transfer',
  program_transfer: 'Program transfer',
}

export const TRANSFER_EVENT_LABEL: Record<TransferEventAction, string> = {
  submitted: 'Request submitted',
  review_started: 'Review started',
  approved: 'Approved — section changed',
  rejected: 'Rejected',
  cancelled: 'Cancelled by student',
  transferred: 'Transferred directly',
}

export function isOpenTransfer(status: TransferStatus) {
  return status === 'submitted' || status === 'under_review'
}

/** "B.Tech CSE · Section A (2024 batch, Semester 3)" */
export function describeSection(section: TransferSection | null) {
  if (!section) return 'Section unavailable'
  return `${section.program_name} · Section ${section.section_name} (${section.batch_name}, ${section.program_semester_name})`
}

export function seatSummary(section: TransferSection) {
  if (section.capacity === null) return `${section.seats_taken} students · no seat limit`
  const free = Math.max(section.capacity - section.seats_taken, 0)
  return `${free} of ${section.capacity} seats free`
}

export function formatTransferDate(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export const TRANSFER_INITIATOR_LABEL: Record<TransferInitiator, string> = {
  student: 'Requested by student',
  admin: 'Transferred by administrator',
  hod: 'Transferred by Head of Department',
}
