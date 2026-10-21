import { useEffect, useState } from 'react'
import { useApiMutation, useApiQuery } from '../../hooks/useApiQuery.ts'
import {
  AdminInvitationError,
  acceptInvitation,
  acceptMembership,
  inspectInvitation,
  recoverInvitationAccount,
} from '../../services/invitations/adminInvitationApi.ts'
import type { AdminInvitationPublicView } from '../../types/platform.ts'
import { useAuth } from '../auth/session/AuthProvider.tsx'
export type Phase =
  | { readonly kind: 'loading' }
  | { readonly kind: 'unusable'; readonly message: string }
  | { readonly kind: 'ready'; readonly invitation: AdminInvitationPublicView }
  | { readonly kind: 'submitting'; readonly invitation: AdminInvitationPublicView }
  | {
      readonly kind: 'accepted'
      readonly institutionName: string
      readonly message: string
      readonly role: 'admin' | 'staff' | 'faculty'
    }

export const inputClass =
  'w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400'

export const labelClass = 'mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-400'

export function formatExpiry(value: string | null): string {
  if (value === null) return 'an unknown time'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString()
}

export function useInvitationAcceptance({ token }: { token: string }) {
  const auth = useAuth()
  const [existingAccount, setExistingAccount] = useState(false)
  const [phase, setPhase] = useState<Phase>({ kind: 'loading' })
  const recoveryMode =
    (phase.kind === 'ready' || phase.kind === 'submitting') && phase.invitation.account_recovery_available === true
  const membershipMode =
    existingAccount ||
    auth.status === 'authenticated' ||
    ((phase.kind === 'ready' || phase.kind === 'submitting') && phase.invitation.status === 'accepted')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const invitationQuery = useApiQuery<AdminInvitationPublicView>(['admin-invitation', token], () =>
    inspectInvitation(token),
  )
  const acceptMutation = useApiMutation<
    Awaited<ReturnType<typeof acceptInvitation>>,
    { password: string; first_name?: string; last_name?: string }
  >({
    mutationFn: (payload) =>
      recoveryMode
        ? recoverInvitationAccount(token)
        : membershipMode && auth.accessToken
          ? acceptMembership(token, auth.accessToken)
          : acceptInvitation(token, payload),
  })

  useEffect(() => {
    if (invitationQuery.data) setPhase({ kind: 'ready', invitation: invitationQuery.data })
    if (invitationQuery.isError) {
      setPhase({
        kind: 'unusable',
        message:
          invitationQuery.error instanceof AdminInvitationError
            ? invitationQuery.error.message
            : 'This invitation link could not be verified.',
      })
    }
  }, [invitationQuery.data, invitationQuery.error, invitationQuery.isError])

  const submit = async (event: React.FormEvent): Promise<void> => {
    event.preventDefault()
    setLocalError(null)
    if (phase.kind !== 'ready') return
    if (!recoveryMode && membershipMode && (!auth.accessToken || auth.status !== 'authenticated')) {
      setLocalError('Sign in with the invited account, then return to this invitation link.')
      return
    }
    if (
      !recoveryMode &&
      membershipMode &&
      auth.user?.email?.trim().toLowerCase() !== phase.invitation.email.trim().toLowerCase()
    ) {
      setLocalError('This invitation belongs to another account. Sign in with the invited address.')
      return
    }
    if (!recoveryMode && !membershipMode && password.length < 8) {
      setLocalError('Choose a password of at least 8 characters.')
      return
    }
    if (!recoveryMode && !membershipMode && password !== confirmPassword) {
      setLocalError('The two passwords do not match.')
      return
    }
    const invitation = phase.invitation
    setPhase({ kind: 'submitting', invitation })
    try {
      const result = await acceptMutation.mutateAsync({
        password: recoveryMode || membershipMode ? '' : password,
        ...(firstName.trim() !== '' ? { first_name: firstName.trim() } : {}),
        ...(lastName.trim() !== '' ? { last_name: lastName.trim() } : {}),
      })
      // Clear the password from component state immediately on success.
      setPassword('')
      setConfirmPassword('')
      setPhase({
        kind: 'accepted',
        institutionName: result.institution_name,
        message: result.message,
        role: result.role,
      })
    } catch (err) {
      // Resolve a possibly committed acceptance before offering any new create.
      // Recovery works after reload too; no password or receipt is persisted.
      setPassword('')
      setConfirmPassword('')
      try {
        const latest = await inspectInvitation(token)
        if (latest.account_recovery_available) {
          setPhase({ kind: 'ready', invitation: latest })
          setLocalError('Your invitation was accepted. Retry account recovery to finish sign-in confirmation.')
          return
        }
      } catch {
        /* Keep the original error when inspection is unavailable. */
      }
      // A terminal failure can never succeed on retry, so stop offering the form.
      if (
        err instanceof AdminInvitationError &&
        (err.isTerminal ||
          err.code === 'INVITATION_RECONCILIATION_REQUIRED' ||
          err.code === 'INVITATION_EMAIL_CONFIRMATION_UNCERTAIN')
      ) {
        setPhase({ kind: 'unusable', message: err.message })
        return
      }
      setPhase({ kind: 'ready', invitation })
      setLocalError(
        err instanceof AdminInvitationError
          ? err.message
          : 'We could not complete your account setup. Please try again.',
      )
    }
  }
  return {
    auth,
    setExistingAccount,
    phase,
    recoveryMode,
    membershipMode,
    password,
    setPassword,
    confirmPassword,
    setConfirmPassword,
    firstName,
    setFirstName,
    lastName,
    setLastName,
    localError,
    submit,
  }
}

export type AdminInvitationPageModel = ReturnType<typeof useInvitationAcceptance>
