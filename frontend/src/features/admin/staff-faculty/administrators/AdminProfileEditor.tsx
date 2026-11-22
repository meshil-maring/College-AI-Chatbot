import { useId, useState } from 'react'
import type { InstitutionAdmin } from '../../../../types/admin/administrators.ts'
import { BUTTON_CLASS, PRIMARY_BUTTON_CLASS } from '../StaffFacultyUI.tsx'
import AdminProfileFields from './AdminProfileFields.tsx'
import { profileDraft, toProfile, validateProfile, type AdminProfileErrors } from './adminProfile.ts'
import type { InstitutionAdminsModel } from './useInstitutionAdmins.ts'

/** Edit an administrator's employee details (the Owner for anyone, an administrator for themselves). */
export default function AdminProfileEditor({
  admin,
  model,
  onDone,
}: {
  admin: InstitutionAdmin
  model: InstitutionAdminsModel
  onDone: () => void
}) {
  const id = useId()
  const [draft, setDraft] = useState(profileDraft(admin.profile))
  const [errors, setErrors] = useState<AdminProfileErrors>({})
  const saving = model.actionKey === `profile:${admin.user_id}`

  async function save() {
    const found = validateProfile(draft)
    setErrors(found)
    if (Object.keys(found).length) return
    const failure = await model.saveProfile(admin, toProfile(draft))
    if (!failure) onDone()
  }

  return (
    <section
      aria-label={`Profile of ${admin.name}`}
      className="w-full space-y-3 rounded-lg border border-line bg-raised p-3"
    >
      <AdminProfileFields idPrefix={id} draft={draft} errors={errors} disabled={saving} onChange={setDraft} />
      <div className="flex flex-wrap justify-end gap-2">
        <button type="button" disabled={saving} onClick={onDone} className={BUTTON_CLASS}>
          Cancel
        </button>
        <button
          type="button"
          disabled={model.actionKey !== null}
          onClick={() => void save()}
          className={PRIMARY_BUTTON_CLASS}
        >
          {saving ? 'Saving…' : 'Save profile'}
        </button>
      </div>
    </section>
  )
}
