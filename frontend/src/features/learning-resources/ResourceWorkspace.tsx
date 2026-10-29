import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import type { LearningResource, ResourceRevision, ResourceView } from '../../types/learningResources.ts'
import type { ResourceContext } from './data/resourceIdentity.ts'
import { useResources } from './data/useResources.ts'
import { resourceError } from '../../services/knowledge/resources.ts'
import WorkspacePageHeader from '../workspace/WorkspacePageHeader.tsx'
import ResourceToolbar from './ResourceToolbar.tsx'
import ResourceList from './ResourceList.tsx'
import ResourceListState from './ResourceListState.tsx'
import ResourceDrawer, { type ResourceSelection } from './details/ResourceDrawer.tsx'
import ResourceChatView from '../chat/resource/ResourceChatView.tsx'
import type { ResourceChatContext } from '../../types/chat.ts'

export default function ResourceWorkspace({
  context,
  isCurrent,
}: {
  context: ResourceContext
  isCurrent: () => boolean
}) {
  const state = useResources(context)
  const [selection, setSelection] = useState<ResourceSelection | null>(null)
  const [accessLost, setAccessLost] = useState(false)
  const [chatResource, setChatResource] = useState<ResourceChatContext | null>(null)
  useEffect(() => {
    if (state.denied) setAccessLost(true)
  }, [state.denied])
  if (accessLost || state.denied)
    return (
      <section role="alert" className="learning-resources-page lr-empty">
        <h1>Learning Resources</h1>
        <p>Your resource access changed. Reload your session to continue.</p>
        <button type="button" className="lr-secondary" onClick={() => window.location.reload()}>
          Reload session
        </button>
      </section>
    )
  if (chatResource) return <ResourceChatView resource={chatResource} onBack={() => setChatResource(null)} />
  const tabs: { key: ResourceView; label: string; allowed: boolean }[] = [
    { key: 'library', label: 'Library', allowed: context.canRead },
    { key: 'own', label: 'My submissions', allowed: context.canCreate },
    { key: 'review', label: 'Admin review', allowed: context.canReview },
  ]
  function open(row: LearningResource | ResourceRevision) {
    setSelection(
      'revision_id' in row
        ? { kind: 'revision', id: row.revision_id }
        : { kind: 'source', id: row.knowledge_source_id },
    )
  }
  return (
    <section className="learning-resources-page" aria-label="Learning Resources" tabIndex={-1}>
      <div className="lr-page-heading">
        <WorkspacePageHeader
          title="Learning Resources"
          description="Manage the knowledge your institution’s chatbot can use. Upload, choose an audience and submit for review."
        />
        {context.canCreate && (
          <button
            type="button"
            className="ui-primary"
            disabled={!state.data || state.query.isError}
            onClick={() => setSelection({ kind: 'create' })}
          >
            <Plus size={18} aria-hidden="true" />
            Add resource
          </button>
        )}
      </div>
      <nav className="lr-tabs" aria-label="Resource views">
        {tabs
          .filter((tab) => tab.allowed)
          .map((tab) => (
            <button
              key={tab.key}
              type="button"
              aria-current={state.view === tab.key ? 'page' : undefined}
              onClick={() => state.setView(tab.key)}
            >
              {tab.label}
            </button>
          ))}
      </nav>
      <div className="lr-library-panel">
        <ResourceToolbar state={state} />
        <div className="lr-list-description">
          <p>
            {state.view === 'library'
              ? 'Published resources available to your audience.'
              : state.view === 'own'
                ? 'Your drafts, submitted revisions and publication history.'
                : 'Review institution revisions and manage publication.'}
          </p>
          <span>Search and filters apply to this page.</span>
        </div>
        {state.data && state.query.isError && (
          <div className="lr-callout lr-warning" role="alert">
            Saved results could not be refreshed. They may be out of date. {resourceError(state.query.error)}
          </div>
        )}
        {state.data && state.query.isFetching && (
          <p role="status" className="lr-updating">
            Updating resources…
          </p>
        )}
        <ResourceListState state={state} />
        {Boolean(state.rows?.length) && <ResourceList rows={state.rows!} onOpen={open} />}
        {state.data && (
          <footer className="lr-pagination">
            <p>
              {state.data.total === 0
                ? '0 resources'
                : state.data.items.length === 0
                  ? `No results on this page · ${state.data.total} resources available`
                  : `${state.offset + 1}–${state.offset + state.data.items.length} of ${state.data.total} resources`}
            </p>
            <div className="lr-actions">
              <button
                type="button"
                className="lr-secondary"
                disabled={state.offset === 0 || state.query.isFetching}
                onClick={() => state.setOffset(Math.max(0, state.offset - 20))}
              >
                Previous
              </button>
              <button
                type="button"
                className="lr-secondary"
                disabled={state.offset + 20 >= state.data.total || state.offset >= 100000 || state.query.isFetching}
                onClick={() => state.setOffset(state.offset + 20)}
              >
                Next
              </button>
            </div>
          </footer>
        )}
      </div>
      {selection && (
        <ResourceDrawer
          context={context}
          selection={selection}
          isCurrent={isCurrent}
          onClose={() => setSelection(null)}
          onSelect={setSelection}
          onAccessLost={() => setAccessLost(true)}
          onAsk={(resource) => {
            setSelection(null)
            setChatResource(resource)
          }}
        />
      )}
    </section>
  )
}
