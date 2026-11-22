import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { queryClient } from '../../../../lib/queryClient.ts'
import {
  getMemberProfile,
  saveMemberProfile,
  setMemberAdditionalDepartments,
  setMemberDepartment,
} from '../../../../services/admin/adminApi.ts'
import type { MembershipRosterEntry } from '../../../../types/admin.ts'
import {
  toInvitation,
  validateStep,
  type DraftErrors,
  type DraftField,
  type MemberDraft,
} from '../invitations/add-member/memberDraft.ts'
import { staffFacultyKeys } from '../staffFacultyKeys.ts'
import { profileToDraft } from './profileDraft.ts'

const sameIds = (a: string[], b: string[]) => a.length === b.length && a.every((id) => b.includes(id))

/**
 * Edit one member's employee profile and departments with the same rules as
 * Add member. Saves the profile first, then only the departments that changed.
 */
export function useEditProfile(accessToken: string, member: MembershipRosterEntry) {
  const query = useQuery(
    {
      queryKey: staffFacultyKeys.profile(accessToken, member.user_id),
      queryFn: () => getMemberProfile(accessToken, member.user_id),
      staleTime: 0,
    },
    queryClient,
  )
  const [draft, setDraft] = useState<MemberDraft | null>(null)
  const [errors, setErrors] = useState<DraftErrors>({})
  const [saving, setSaving] = useState(false)
  const [serverError, setServerError] = useState<string | null>(null)
  const original = useRef<MemberDraft | null>(null)

  // Start editing from the saved profile once it has loaded.
  useEffect(() => {
    if (query.data && original.current === null) {
      original.current = profileToDraft(member, query.data)
      setDraft(original.current)
    }
  }, [query.data, member])

  function update<K extends DraftField>(field: K, value: MemberDraft[K]) {
    setDraft((current) => {
      if (!current) return current
      const next = { ...current, [field]: value }
      if (field === 'department_id') {
        next.additional_department_ids = current.additional_department_ids.filter((id) => id !== value)
      }
      return next
    })
    setErrors((current) => ({ ...current, [field]: undefined }))
  }

  /** Returns true when everything was saved. */
  async function save(): Promise<boolean> {
    if (!draft || !original.current) return false
    const found = { ...validateStep(0, draft), ...validateStep(1, draft) }
    setErrors(found)
    if (Object.values(found).some(Boolean)) return false
    setSaving(true)
    setServerError(null)
    const request = toInvitation(draft)
    try {
      await saveMemberProfile(accessToken, member.user_id, request.profile)
      if (draft.department_id !== original.current.department_id) {
        await setMemberDepartment(accessToken, member.user_id, draft.department_id)
      }
      const additional = request.additional_department_ids ?? []
      if (!sameIds(additional, original.current.additional_department_ids)) {
        await setMemberAdditionalDepartments(accessToken, member.user_id, additional)
      }
      return true
    } catch (cause) {
      setServerError(cause instanceof Error ? cause.message : 'The profile could not be saved.')
      return false
    } finally {
      setSaving(false)
      // Show whatever was saved, even after a partial failure.
      await queryClient.invalidateQueries({ queryKey: staffFacultyKeys.roster(accessToken) })
      await queryClient.invalidateQueries({ queryKey: staffFacultyKeys.profile(accessToken, member.user_id) })
    }
  }

  return {
    draft,
    errors,
    update,
    save,
    saving,
    serverError,
    loading: query.isPending,
    loadError: query.error
      ? query.error instanceof Error
        ? query.error.message
        : 'Could not load the profile.'
      : null,
  }
}

export type EditProfileModel = ReturnType<typeof useEditProfile>
