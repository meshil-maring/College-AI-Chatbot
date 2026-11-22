import { useState } from 'react'
import type { AdminAccessArea, InstitutionAdmin } from '../../../../types/admin/administrators.ts'
import { BUTTON_CLASS, PRIMARY_BUTTON_CLASS } from '../StaffFacultyUI.tsx'
import AccessAreasField from './AccessAreasField.tsx'
import { ALL_AREAS, toAccess } from './accessAreas.ts'
import type { InstitutionAdminsModel } from './useInstitutionAdmins.ts'

/** Owner only: change which areas another administrator may manage. */
export default function AdminAccessEditor({
  admin,
  model,
  onDone,
}: {
  admin: InstitutionAdmin
  model: InstitutionAdminsModel
  onDone: () => void
}) {
  const [areas, setAreas] = useState<AdminAccessArea[]>(admin.access_areas ?? ALL_AREAS)
  const saving = model.actionKey === `access:${admin.user_id}`

  async function save() {
    const failure = await model.setAccess(admin, toAccess(areas))
    if (!failure) onDone()
  }

  return (
    <div className="w-full space-y-3 rounded-lg border border-line bg-raised p-3">
      <AccessAreasField legend={`Access for ${admin.name}`} value={areas} disabled={saving} onChange={setAreas} />
      <p className="text-xs text-muted">
        The server applies changes on their next request; their menu updates when they reload the page.
      </p>
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
          {saving ? 'Saving…' : 'Save access'}
        </button>
      </div>
    </div>
  )
}
