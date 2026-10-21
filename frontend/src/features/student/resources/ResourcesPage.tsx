import { getMyResources } from '../../../services/students/studentApi.ts'
import { useStudentResource } from '../shared/useStudentResource.ts'
import { SectionCard } from '../shared/SectionState.tsx'
import ResourcesPanel from './ResourcesPanel.tsx'

/**
 * Phase 6.16.3 — Learning Resources page. `20` stays well inside the backend's
 * resource limit contract (`student_resources.MAX_RESOURCE_LIMIT === 50`).
 * The endpoint returns safe metadata only — there is NO storage-access or
 * download contract — so the page renders metadata without any open/link
 * action, and adds no source-type filter the backend does not support (the
 * endpoint's only query field is `limit`).
 */
export function ResourcesPage() {
  const resources = useStudentResource(
    (token) => getMyResources(token, 20),
    'Unable to load learning resources.',
    '',
    'resources-20',
  )
  return (
    <SectionCard title="Learning resources" headingId="student-page-resources">
      <ResourcesPanel resources={resources} />
    </SectionCard>
  )
}
