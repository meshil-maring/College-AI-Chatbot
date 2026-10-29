import type { LearningResource } from '../../../types/learningResources.ts'
import { AudienceBadge } from '../ResourceBadges.tsx'
import { typeLabel } from '../resourcePresentation.ts'

export default function ResourceInformation({ resource }: { resource: LearningResource }) {
  return (
    <section className="lr-information" aria-label="Resource information">
      <AudienceBadge resource={resource} />
      <p>{resource.description || 'No description provided.'}</p>
      <dl>
        <div>
          <dt>Resource type</dt>
          <dd>{typeLabel(resource.source_type)}</dd>
        </div>
        <div>
          <dt>Available from</dt>
          <dd>{resource.effective_from || 'After publication'}</dd>
        </div>
        <div>
          <dt>Available until</dt>
          <dd>{resource.effective_until || 'No end date'}</dd>
        </div>
      </dl>
    </section>
  )
}
