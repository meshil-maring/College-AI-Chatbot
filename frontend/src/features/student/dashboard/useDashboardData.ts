/**
 * Server state behind the student dashboard.
 *
 * Reuses the semester-registration and transfer query factories so the
 * dashboard shares one cache entry with the full pages it links to. Each read
 * runs only when the student holds the matching grant; the server still
 * enforces every permission and tenant rule.
 */

import { useContext, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { queryClient } from '../../../lib/queryClient.ts'
import { AdminApiError } from '../../../services/admin/http.ts'
import type { StudentSemester } from '../../../types/semesterRegistration.ts'
import type { TransferRequest } from '../../../types/transfer.ts'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
import { isOpenTransfer } from '../../transfers/transferLabels.ts'
import { studentRegistrationOptions } from '../registration/registrationQueries.ts'
import { studentTransfersOptions } from '../transfer/useStudentTransfers.ts'
import { StudentAccessContext, type StudentAccessDenial } from '../shared/useStudentResource.ts'

export type DashboardStatus = 'unavailable' | 'loading' | 'error' | 'loaded'

export interface DashboardRead<T> {
  readonly status: DashboardStatus
  readonly data: T | null
  readonly retry: () => void
}

const DENIALS: readonly string[] = ['STUDENT_NOT_APPROVED', 'STUDENT_INACTIVE', 'ACCOUNT_INACTIVE']

/** The term running today, otherwise the most recently started one. */
export function pickCurrentSemester(items: readonly StudentSemester[], now = new Date()): StudentSemester | null {
  if (items.length === 0) return null
  const today = now.getTime()
  const running = items.find(
    (item) => new Date(item.start_date).getTime() <= today && today <= new Date(item.end_date).getTime(),
  )
  if (running) return running
  return [...items].sort((a, b) => b.start_date.localeCompare(a.start_date))[0]
}

/** Share of the term that has elapsed, 0–100, or null for unusable dates. */
export function termProgress(semester: StudentSemester, now = new Date()): number | null {
  const start = new Date(semester.start_date).getTime()
  const end = new Date(semester.end_date).getTime()
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return null
  const ratio = (now.getTime() - start) / (end - start)
  return Math.round(Math.min(1, Math.max(0, ratio)) * 100)
}

function toRead<T>(
  enabled: boolean,
  query: { isPending: boolean; isError: boolean; data: unknown; refetch: () => unknown },
  data: T | null,
): DashboardRead<T> {
  const retry = () => void query.refetch()
  if (!enabled) return { status: 'unavailable', data: null, retry }
  if (query.isError) return { status: 'error', data: null, retry }
  if (query.isPending) return { status: 'loading', data: null, retry }
  return { status: 'loaded', data, retry }
}

export function useDashboardData(canReadRegistration: boolean, canReadTransfers: boolean) {
  const { accessToken, user, role, sessionGeneration } = useAuth()
  const reportDenial = useContext(StudentAccessContext)
  const institutionId = user?.institution_id ?? ''
  const token = accessToken ?? ''
  const ready = accessToken !== null && institutionId !== '' && role === 'student'
  const identity = JSON.stringify([
    sessionGeneration ?? 0,
    user?.user_id,
    institutionId,
    role,
    [...(user?.effective_permissions ?? [])].sort(),
  ])

  const semesters = useQuery(
    { ...studentRegistrationOptions(identity, institutionId, token), enabled: ready && canReadRegistration },
    queryClient,
  )
  const transfers = useQuery(
    { ...studentTransfersOptions(identity, institutionId, token), enabled: ready && canReadTransfers },
    queryClient,
  )

  const error = semesters.error ?? transfers.error
  useEffect(() => {
    if (error instanceof AdminApiError && DENIALS.includes(error.code ?? ''))
      reportDenial?.(error.code as StudentAccessDenial)
  }, [error, reportDenial])

  const semester = semesters.data ? pickCurrentSemester(semesters.data.items) : null
  const open: TransferRequest[] = (transfers.data?.requests ?? []).filter((item) => isOpenTransfer(item.status))
  return {
    semester: toRead(ready && canReadRegistration, semesters, semester),
    openTransfers: toRead(ready && canReadTransfers, transfers, open),
  }
}
