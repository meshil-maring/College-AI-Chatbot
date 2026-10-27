import type { AcademicCatalogue, AcademicEntity } from '../../../../types/academicSetup.ts'
import { academicParents } from '../academicSetupParents.ts'
import { getAcademicArea, quickActions } from './academicOverviewModel.ts'

interface Props {
  catalogue?: AcademicCatalogue
  busy: boolean
  compact?: boolean
  onCreate: (entity: AcademicEntity) => void
}

export default function AcademicQuickLinks({ catalogue, busy, compact = false, onCreate }: Props) {
  return (
    <div className={compact ? 'academic-action-list' : 'academic-quick-grid'}>
      {quickActions.map((action) => {
        const area = getAcademicArea(action.page)!
        const entity = area.entity
        // Only server-advertised existing capabilities can expose a write action.
        if (entity && catalogue && (!catalogue.records[entity] || !catalogue.manageable.includes(entity))) return null
        const issue = entity && catalogue ? academicParents(catalogue, entity).issue : null
        const disabled = busy || !entity || !catalogue || Boolean(issue)
        const reason = !entity ? 'Not connected' : (issue ?? (!catalogue ? 'Access unavailable' : undefined))
        return (
          <button
            type="button"
            key={action.page}
            disabled={disabled}
            aria-label={action.label}
            title={reason}
            aria-describedby={disabled ? `academic-action-${compact ? 'menu' : 'tile'}-${action.page}` : undefined}
            onClick={() => {
              if (entity && !disabled) onCreate(entity)
            }}
          >
            <area.icon aria-hidden="true" />
            <span>{action.label}</span>
            {disabled && (
              <small id={`academic-action-${compact ? 'menu' : 'tile'}-${action.page}`}>{reason ?? 'Updating…'}</small>
            )}
          </button>
        )
      })}
    </div>
  )
}
