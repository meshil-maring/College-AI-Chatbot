import { useId } from 'react'
import type { AdminAccessArea } from '../../../../types/admin/administrators.ts'
import { ACCESS_AREAS } from './accessAreas.ts'

interface Props {
  legend: string
  value: readonly AdminAccessArea[]
  disabled?: boolean
  onChange: (areas: AdminAccessArea[]) => void
}

/** Tick the areas an administrator may manage. Everything ticked means full access. */
export default function AccessAreasField({ legend, value, disabled = false, onChange }: Props) {
  const id = useId()
  return (
    <fieldset className="space-y-2" disabled={disabled}>
      <legend className="text-sm font-medium text-content">{legend}</legend>
      <div className="grid gap-2 md:grid-cols-2">
        {ACCESS_AREAS.map((area) => (
          <label key={area.value} className="flex cursor-pointer items-start gap-3 text-sm">
            <input
              type="checkbox"
              aria-label={area.label}
              aria-describedby={`${id}-${area.value}`}
              checked={value.includes(area.value)}
              onChange={(event) =>
                onChange(
                  event.target.checked
                    ? ACCESS_AREAS.map((item) => item.value).filter(
                        (item) => item === area.value || value.includes(item),
                      )
                    : value.filter((item) => item !== area.value),
                )
              }
              className="mt-0.5 size-5 accent-[var(--ui-accent)]"
            />
            <span className="flex flex-col">
              <span className="text-content">{area.label}</span>
              <span id={`${id}-${area.value}`} className="text-xs text-muted">
                {area.description}
              </span>
            </span>
          </label>
        ))}
      </div>
      <p className="text-xs text-muted">
        Every administrator keeps their own profile, the AI Assistant and read-only academic lists.
      </p>
    </fieldset>
  )
}
