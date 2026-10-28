import { useCallback, useEffect, useState } from 'react'
import {
  PlatformInstitutionError,
  createInvitation,
  getAdminRoster,
} from '../../../services/platform/platformInstitutionsApi.ts'
import type {
  AdminInvitationCreated,
  AdminInvitationResend,
  AdminRoster,
  AdminRosterEntry,
} from '../../../types/platform.ts'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
export const inputClass =
  'w-full rounded-lg border border-control bg-surface px-3 py-2 text-sm text-content placeholder-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent'

export const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-muted'

export function useAdminRoster({
  institutionId,
  institutionCode,
  onChanged,
}: {
  institutionId: string
  institutionCode: string
  /** Let the parent refresh its institution detail (admin_count) afterwards. */
  onChanged?: () => void
}) {
  const { accessToken } = useAuth()
  const token = accessToken ?? ''

  const [roster, setRoster] = useState<AdminRoster | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<'invite' | 'cancel' | 'resend' | 'revoke' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const [showInvite, setShowInvite] = useState(false)
  const [email, setEmail] = useState('')
  const [created, setCreated] = useState<AdminInvitationCreated | null>(null)
  // Phase 7.15: the same one-time-link reveal, reused after a resend so an
  // operator who loses the emailed message still has a fallback link.
  const [resent, setResent] = useState<AdminInvitationResend | null>(null)
  const [copied, setCopied] = useState(false)
  const [confirmRevoke, setConfirmRevoke] = useState<AdminRosterEntry | null>(null)
  const [confirmResend, setConfirmResend] = useState<AdminRosterEntry | null>(null)

  const refresh = useCallback(async (): Promise<void> => {
    if (token === '') return
    setLoading(true)
    try {
      setRoster(await getAdminRoster(token, institutionId))
    } catch (err) {
      setError(
        err instanceof PlatformInstitutionError ? err.message : 'Could not load the admin roster. Please try again.',
      )
    } finally {
      setLoading(false)
    }
  }, [token, institutionId])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const run = useCallback(
    async (action: 'invite' | 'cancel' | 'resend' | 'revoke', operation: () => Promise<string>): Promise<void> => {
      setBusy(action)
      setError(null)
      setNotice(null)
      try {
        setNotice(await operation())
        await refresh()
        onChanged?.()
      } catch (err) {
        setError(err instanceof PlatformInstitutionError ? err.message : 'Something went wrong. Please try again.')
      } finally {
        setBusy(null)
      }
    },
    [refresh, onChanged],
  )

  const invite = (): Promise<void> =>
    run('invite', async () => {
      const result = await createInvitation(token, institutionId, { email: email.trim() })
      // Raw-link fallback is limited to responses from the explicit local/test
      // capture providers. A production provider response never renders it.
      setCreated(
        result.email_delivery?.provider === 'local' || result.email_delivery?.provider === 'test' ? result : null,
      )
      setCopied(false)
      setEmail('')
      setShowInvite(false)
      if (result.email_delivery?.status === 'pending') return 'Invitation email queued'
      return result.email_delivery?.status === 'sent'
        ? 'Invitation sent'
        : 'Invitation could not be delivered. Try again later.'
    })

  return {
    institutionId,
    institutionCode,
    token,
    roster,
    loading,
    busy,
    error,
    setError,
    notice,
    setNotice,
    showInvite,
    setShowInvite,
    email,
    setEmail,
    created,
    setCreated,
    resent,
    setResent,
    copied,
    setCopied,
    confirmRevoke,
    setConfirmRevoke,
    confirmResend,
    setConfirmResend,
    run,
    invite,
  }
}

export type AdminRosterPanelModel = ReturnType<typeof useAdminRoster>
