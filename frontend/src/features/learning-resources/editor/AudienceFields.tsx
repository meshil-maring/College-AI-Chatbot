import { Globe2, LockKeyhole, Users } from 'lucide-react'
import type { ResourceAudience } from '../../../types/learningResources.ts'
import { audienceRoles } from '../resourcePresentation.ts'

const modes = [
  { value: 'public', label: 'Public', description: 'Anyone visiting your institution’s chatbot.', icon: Globe2 },
  {
    value: 'institution',
    label: 'Institution members',
    description: 'Signed-in members of your institution.',
    icon: Users,
  },
  {
    value: 'roles',
    label: 'Selected roles',
    description: 'Only the institution roles you choose below.',
    icon: LockKeyhole,
  },
] as const
export default function AudienceFields({
  value,
  disabled,
  onChange,
}: {
  value: ResourceAudience
  disabled: boolean
  onChange: (audience: ResourceAudience) => void
}) {
  return (
    <fieldset className="lr-audience-fields" disabled={disabled} aria-describedby="resource-audience-help">
      <legend>Who can use this resource?</legend>
      <p id="resource-audience-help" className="lr-help">
        This audience takes effect after admin publication.
      </p>
      <div className="lr-audience-options">
        {modes.map(({ value: mode, label, description, icon: Icon }) => (
          <label key={mode} className={value.mode === mode ? 'is-selected' : ''}>
            <input
              type="radio"
              name="resource-audience"
              value={mode}
              checked={value.mode === mode}
              onChange={() => onChange({ mode, roles: mode === 'roles' ? value.roles : [] })}
            />
            <Icon aria-hidden="true" />
            <span>
              <strong>{label}</strong>
              <small>{description}</small>
            </span>
          </label>
        ))}
      </div>
      {value.mode === 'roles' && (
        <div className="lr-role-options" role="group" aria-label="Selected audience roles">
          {audienceRoles.map(({ value: role, label }) => (
            <label key={role}>
              <input
                type="checkbox"
                checked={value.roles.includes(role)}
                onChange={(event) =>
                  onChange({
                    ...value,
                    roles: event.target.checked ? [...value.roles, role] : value.roles.filter((item) => item !== role),
                  })
                }
              />
              {label}
            </label>
          ))}
          {!value.roles.length && (
            <p className="lr-help">You can save a private draft now. Select at least one role before submitting.</p>
          )}
        </div>
      )}
      {value.mode === 'public' && (
        <p className="lr-callout lr-info">
          After publication, visitors can receive chatbot answers based on these files without signing in.
        </p>
      )}
    </fieldset>
  )
}
