import { useState } from 'react'
import { updateInstitution } from '../../../services/platform/platformInstitutionsApi.ts'
import type { InstitutionDetail } from '../../../types/platform.ts'
import { useAuth } from '../../auth/session/AuthProvider.tsx'
/** Which mutation is in flight, so the UI can disable conflicting actions. */
export type BusyAction = 'create' | 'save' | 'suspend' | 'activate' | 'assign' | null

export function useInstitutionDetail({
  institution,
  busy,
  onSaved,
  onSuspend,
  onActivate,
  onAssign,
  onRosterChanged,
}: {
  institution: InstitutionDetail
  busy: BusyAction
  onSaved: (detail: InstitutionDetail) => void
  onSuspend: () => void
  onActivate: () => void
  onAssign: (email: string) => void
  /** Refresh the parent so `admin_count` reflects a roster change. */
  onRosterChanged?: () => void
}) {
  const { accessToken } = useAuth()
  const [name, setName] = useState(institution.name)
  const [code, setCode] = useState(institution.code)
  const [displayName, setDisplayName] = useState(institution.display_name ?? '')
  const [welcomeMessage, setWelcomeMessage] = useState(institution.welcome_message ?? '')
  const [primaryColor, setPrimaryColor] = useState(institution.primary_color ?? '')
  const [localError, setLocalError] = useState<string | null>(null)
  const [confirmSuspend, setConfirmSuspend] = useState(false)
  const [confirmApproval, setConfirmApproval] = useState(false)
  const [showAssign, setShowAssign] = useState(false)
  const [adminEmail, setAdminEmail] = useState('')

  const [saving, setSaving] = useState(false)

  /**
   * Persist the edited configuration through the same authenticated client the
   * rest of this screen uses, sending ONLY the fields that actually changed so
   * a partial update can never blank an untouched value.
   */
  const saveConfiguration = async (): Promise<void> => {
    setLocalError(null)
    const input: Record<string, string> = {}
    if (name.trim() !== '' && name.trim() !== institution.name) input.name = name.trim()
    if (code.trim() !== '' && code.trim() !== institution.code) input.code = code.trim()
    if (displayName.trim() !== (institution.display_name ?? '')) {
      input.display_name = displayName.trim()
    }
    if (welcomeMessage.trim() !== (institution.welcome_message ?? '')) {
      input.welcome_message = welcomeMessage.trim()
    }
    if (primaryColor.trim() !== (institution.primary_color ?? '')) {
      input.primary_color = primaryColor.trim()
    }
    if (Object.keys(input).length === 0) return
    setSaving(true)
    try {
      onSaved(await updateInstitution(accessToken ?? '', institution.id, input))
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : 'Could not save the configuration. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return {
    institution,
    busy,
    onSuspend,
    onActivate,
    onAssign,
    onRosterChanged,
    name,
    setName,
    code,
    setCode,
    displayName,
    setDisplayName,
    welcomeMessage,
    setWelcomeMessage,
    primaryColor,
    setPrimaryColor,
    localError,
    confirmSuspend,
    setConfirmSuspend,
    confirmApproval,
    setConfirmApproval,
    showAssign,
    setShowAssign,
    adminEmail,
    setAdminEmail,
    saving,
    saveConfiguration,
  }
}

export type InstitutionDetailPanelModel = ReturnType<typeof useInstitutionDetail>
