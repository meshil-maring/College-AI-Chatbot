import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createRevision, resourceError, ResourceApiError } from '../../../services/knowledge/resources.ts'
import { accessDenied, resourceKeys, resourceRevisionOptions, resourceSourceOptions } from '../data/queries.ts'
import { canCloneResource, type ResourceContext } from '../data/resourceIdentity.ts'
import { useResourceActions } from '../data/useResourceActions.ts'
import ResourceEditor from '../editor/ResourceEditor.tsx'
import ResourceDrawerFrame from './ResourceDrawerFrame.tsx'
import ResourceFiles from './ResourceFiles.tsx'
import ResourceInformation from './ResourceInformation.tsx'
import RevisionPanel from './RevisionPanel.tsx'
import AskResourceAi from '../../chat/resource/AskResourceAi.tsx'
import type { ResourceChatContext } from '../../../types/chat.ts'

export type ResourceSelection = { kind: 'create' } | { kind: 'source' | 'revision'; id: string }
export default function ResourceDrawer({
  context,
  selection,
  isCurrent,
  onClose,
  onSelect,
  onAccessLost,
  onAsk,
}: {
  context: ResourceContext
  selection: ResourceSelection
  isCurrent: () => boolean
  onClose: () => void
  onSelect: (selection: ResourceSelection) => void
  onAccessLost: () => void
  onAsk: (resource: ResourceChatContext) => void
}) {
  const client = useQueryClient()
  const [dirty, setDirty] = useState(false)
  const [epoch, setEpoch] = useState(0)
  const mounted = useRef(true)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])
  const actions = useResourceActions({ context, isCurrent, onAccessLost })
  const id = selection.kind === 'create' ? '' : selection.id
  const source = useQuery({ ...resourceSourceOptions(context, id), enabled: selection.kind === 'source' })
  const revision = useQuery({ ...resourceRevisionOptions(context, id), enabled: selection.kind === 'revision' })
  const query = selection.kind === 'revision' ? revision : source
  const denied = accessDenied(query.error)
  const missing = query.error instanceof ResourceApiError && query.error.status === 404
  const data = denied || missing ? undefined : query.data
  useEffect(() => {
    if (denied) onAccessLost()
  }, [denied, onAccessLost])
  useEffect(() => {
    if (missing && isCurrent()) void client.invalidateQueries({ queryKey: resourceKeys.lists(context.identity) })
  }, [missing, client, context.identity, isCurrent])
  const fresh = !query.isError && !query.isFetching
  const title = selection.kind === 'create' ? 'Add resource' : (data?.title ?? 'Resource details')
  async function reload() {
    const result = await query.refetch()
    if (!mounted.current || !isCurrent() || !result.isSuccess) return
    setDirty(false)
    setEpoch((value) => value + 1)
    actions.clear()
    await client.invalidateQueries({ queryKey: resourceKeys.lists(context.identity) })
  }
  return (
    <ResourceDrawerFrame
      title={title}
      busy={actions.saving}
      dirty={dirty}
      onClose={onClose}
      onReload={selection.kind === 'create' ? undefined : reload}
    >
      {actions.error && (
        <p className="lr-callout lr-danger" role="alert">
          {actions.error}
        </p>
      )}
      {actions.notice && (
        <p className="lr-callout lr-success" role="status">
          {actions.notice}
        </p>
      )}
      {actions.saving && actions.activity === 'retry' && (
        <p role="status" className="lr-updating">
          Retrying indexing…
        </p>
      )}
      {actions.blocked && (
        <p className="lr-help">
          {selection.kind === 'create'
            ? 'Check My submissions before creating another draft; the previous request may have saved.'
            : 'Reload the saved revision to check its current files and review state before making another change.'}
        </p>
      )}
      {selection.kind === 'create' ? (
        <ResourceEditor
          context={context}
          actions={actions}
          disabled={!context.canCreate}
          onSaved={(saved) => {
            setDirty(false)
            onSelect({ kind: 'revision', id: saved.revision_id })
          }}
          onDirty={setDirty}
        />
      ) : (
        <>
          {query.isFetching && (
            <p role="status" className="lr-updating">
              Refreshing resource details…
            </p>
          )}
          {query.isError && (
            <p role="alert" className="lr-callout lr-warning">
              {resourceError(query.error)}
              {data ? ' Saved details are shown; refresh before making changes.' : ''}
            </p>
          )}
          {!data && query.fetchStatus === 'paused' && (
            <p role="status">You appear to be offline. Reconnect to load this resource.</p>
          )}
          {data && selection.kind === 'revision' && revision.data ? (
            <RevisionPanel
              key={`${revision.data.revision_id}:${epoch}`}
              context={context}
              revision={revision.data}
              actions={actions}
              disabled={!fresh}
              onDirty={setDirty}
              onOpen={(saved) => onSelect({ kind: 'revision', id: saved.revision_id })}
            />
          ) : data ? (
            <>
              <ResourceInformation resource={data} />
              <ResourceFiles files={data.documents} />
              <AskResourceAi
                context={context}
                sourceId={data.knowledge_source_id}
                disabled={!fresh || data.documents.length === 0}
                isCurrent={isCurrent}
                onReady={onAsk}
              />
              {canCloneResource(context, data) && (
                <div className="lr-form-footer">
                  <p className="lr-help">Create a draft to propose new files or a different audience.</p>
                  <button
                    type="button"
                    className="ui-primary"
                    disabled={!fresh || actions.saving || actions.blocked}
                    onClick={() =>
                      void actions
                        .run(() => createRevision(context.accessToken, data.knowledge_source_id))
                        .then((saved) => {
                          if (saved) onSelect({ kind: 'revision', id: saved.revision_id })
                        })
                    }
                  >
                    Create new revision
                  </button>
                </div>
              )}
            </>
          ) : null}
        </>
      )}
    </ResourceDrawerFrame>
  )
}
